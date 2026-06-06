"use client";

import { useCallback, useEffect, useState } from "react";
import AddNote from "@/components/AddNote";
import AskQuestion from "@/components/AskQuestion";
import NotesList from "@/components/NotesList";
import { getNotes, Note } from "@/lib/api";

export default function Home() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loadingNotes, setLoadingNotes] = useState(true);

  const fetchNotes = useCallback(async () => {
    try {
      const data = await getNotes();
      setNotes(data);
    } catch (err) {
      console.error("Failed to load notes:", err);
    } finally {
      setLoadingNotes(false);
    }
  }, []);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-white text-sm font-bold select-none">S</span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">SmartNotes AI</h1>
          <span className="text-xs text-gray-400 hidden sm:block">RAG-powered study assistant</span>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="space-y-6">
          <AddNote onNoteAdded={fetchNotes} />
          <NotesList notes={notes} loading={loadingNotes} onDeleted={fetchNotes} />
        </div>
        <div className="lg:sticky lg:top-24">
          <AskQuestion />
        </div>
      </div>
    </main>
  );
}
