import logging
from typing import Optional

from openai import OpenAI
from sentence_transformers import SentenceTransformer
from settings import settings

logger = logging.getLogger(__name__)

_embedding_model: Optional[SentenceTransformer] = None
_chroma_collection = None
_upstash_index = None


def _use_upstash() -> bool:
    return bool(settings.upstash_vector_rest_url and settings.upstash_vector_rest_token)


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def get_upstash_index():
    global _upstash_index
    if _upstash_index is None:
        from upstash_vector import Index
        _upstash_index = Index(
            url=settings.upstash_vector_rest_url,
            token=settings.upstash_vector_rest_token,
        )
    return _upstash_index


def get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        client = chromadb.PersistentClient(path=settings.chroma_dir)
        ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        _chroma_collection = client.get_or_create_collection(
            name="notes",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def embed_note(note_id: str, content: str) -> int:
    chunks = chunk_text(content)

    if _use_upstash():
        model = get_embedding_model()
        index = get_upstash_index()
        _delete_upstash_chunks(note_id)
        embeddings = model.encode(chunks)
        vectors = [
            {
                "id": f"{note_id}_chunk_{i}",
                "vector": embeddings[i].tolist(),
                "metadata": {"note_id": note_id, "chunk_index": i, "text": chunk},
            }
            for i, chunk in enumerate(chunks)
        ]
        index.upsert(vectors=vectors)
    else:
        collection = get_chroma_collection()
        existing = collection.get(where={"note_id": note_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
        ids = [f"{note_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"note_id": note_id, "chunk_index": i} for i in range(len(chunks))]
        collection.add(ids=ids, documents=chunks, metadatas=metadatas)

    return len(chunks)


def _delete_upstash_chunks(note_id: str, max_chunks: int = 200) -> None:
    index = get_upstash_index()
    ids = [f"{note_id}_chunk_{i}" for i in range(max_chunks)]
    index.delete(ids=ids)


def delete_note_vectors(note_id: str) -> None:
    if _use_upstash():
        _delete_upstash_chunks(note_id)
    else:
        collection = get_chroma_collection()
        existing = collection.get(where={"note_id": note_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])


def query_notes(question: str, n_results: int = 3) -> list[dict]:
    if _use_upstash():
        model = get_embedding_model()
        index = get_upstash_index()
        embedding = model.encode([question])[0].tolist()
        results = index.query(vector=embedding, top_k=n_results, include_metadata=True)
        return [
            {
                "note_id": r.metadata["note_id"],
                "chunk_index": int(r.metadata["chunk_index"]),
                "text": r.metadata["text"],
            }
            for r in results
            if r.metadata
        ]
    else:
        collection = get_chroma_collection()
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_texts=[question],
            n_results=min(n_results, count),
        )
        sources = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                sources.append({
                    "note_id": metadata["note_id"],
                    "chunk_index": int(metadata["chunk_index"]),
                    "text": doc,
                })
        return sources


def ask_llm(question: str, sources: list[dict]) -> str:
    if not sources:
        return (
            "I don't have any relevant notes to answer this question. "
            "Please add and embed some notes first."
        )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )

    context = "\n\n".join(
        f"[Note {s['note_id']}, chunk {s['chunk_index']}]: {s['text']}"
        for s in sources
    )

    response = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful study assistant. Answer questions ONLY from the "
                    "provided context from the user's notes. Always cite which note(s) you "
                    "used (by note_id). If the context is insufficient, say you don't know "
                    "based on the available notes."
                ),
            },
            {
                "role": "user",
                "content": f"Context from notes:\n\n{context}\n\nQuestion: {question}",
            },
        ],
    )
    return response.choices[0].message.content
