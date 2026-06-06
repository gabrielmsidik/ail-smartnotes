import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, engine, Base
from models import Note
from schemas import (
    NoteCreate,
    NoteResponse,
    NoteListItem,
    EmbedResponse,
    ChatRequest,
    ChatResponse,
    Source,
)
from rag import embed_note as rag_embed, query_notes, ask_llm, delete_note_vectors
from settings import settings

# test github actions pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("DB tables ready")
    yield


app = FastAPI(title="SmartNotes AI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(body: NoteCreate, db: Session = Depends(get_db)):
    title = body.title
    if not title or not title.strip():
        first_line = body.content.strip().splitlines()[0]
        title = first_line[:100] if first_line else "Untitled"

    note = Note(id=uuid.uuid4(), title=title, content=body.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.post("/notes/{note_id}/embed", response_model=EmbedResponse)
def embed_note(note_id: uuid.UUID, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    try:
        chunks_created = rag_embed(str(note_id), note.content)
    except Exception as exc:
        logger.error("Embedding failed for %s: %s", note_id, exc)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}")

    note.embedded = True
    db.commit()
    return {"id": note_id, "chunks_created": chunks_created}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    try:
        sources = query_notes(body.question)
        answer = ask_llm(body.question, sources)
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")

    return {
        "answer": answer,
        "sources": [Source(**s) for s in sources],
    }


@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: uuid.UUID, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.embedded:
        try:
            delete_note_vectors(str(note_id))
        except Exception as exc:
            logger.error("Failed to delete vectors for %s: %s", note_id, exc)

    db.delete(note)
    db.commit()
    return Response(status_code=204)


@app.get("/notes", response_model=list[NoteListItem])
def list_notes(db: Session = Depends(get_db)):
    notes = db.query(Note).order_by(Note.created_at.desc()).all()
    return [
        NoteListItem(
            id=note.id,
            title=note.title,
            content_preview=(
                note.content[:200] + "…" if len(note.content) > 200 else note.content
            ),
            embedded=note.embedded,
            created_at=note.created_at,
        )
        for note in notes
    ]
