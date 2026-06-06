const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Note {
  id: string;
  title: string | null;
  content_preview: string;
  embedded: boolean;
  created_at: string;
}

export interface NoteDetail {
  id: string;
  title: string | null;
  content: string;
  embedded: boolean;
  created_at: string;
}

export interface Source {
  note_id: string;
  chunk_index: number;
  text: string;
}

export interface ChatResult {
  answer: string;
  sources: Source[];
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // use default detail
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function getNotes(): Promise<Note[]> {
  const res = await fetch(`${API_URL}/notes`);
  return handleResponse<Note[]>(res);
}

export async function createNote(title: string, content: string): Promise<NoteDetail> {
  const res = await fetch(`${API_URL}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title.trim() || undefined, content }),
  });
  return handleResponse<NoteDetail>(res);
}

export async function embedNote(id: string): Promise<{ id: string; chunks_created: number }> {
  const res = await fetch(`${API_URL}/notes/${id}/embed`, { method: "POST" });
  return handleResponse<{ id: string; chunks_created: number }>(res);
}

export async function askQuestion(question: string): Promise<ChatResult> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return handleResponse<ChatResult>(res);
}

export async function deleteNote(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/notes/${id}`, { method: "DELETE" });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // use default detail
    }
    throw new Error(detail);
  }
}
