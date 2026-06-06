"use client";

import { useState } from "react";
import { Note, deleteNote } from "@/lib/api";

interface Props {
  notes: Note[];
  loading: boolean;
  onDeleted: () => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="w-4 h-4"
    >
      <path
        fillRule="evenodd"
        d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function NotesList({ notes, loading, onDeleted }: Props) {
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");

  async function handleDelete(note: Note) {
    if (!window.confirm(`Delete "${note.title ?? "Untitled"}"? This cannot be undone.`)) return;

    setDeleting((prev) => new Set(prev).add(note.id));
    setError("");
    try {
      await deleteNote(note.id);
      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting((prev) => {
        const next = new Set(prev);
        next.delete(note.id);
        return next;
      });
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Your Notes{" "}
        {!loading && (
          <span className="text-sm font-normal text-gray-400">({notes.length})</span>
        )}
      </h2>

      {error && (
        <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-gray-400">Loading…</div>
      ) : notes.length === 0 ? (
        <div className="text-sm text-gray-400">No notes yet. Add one above!</div>
      ) : (
        <ul className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
          {notes.map((note) => (
            <li
              key={note.id}
              className="p-4 border border-gray-100 rounded-xl hover:border-gray-200 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm font-medium text-gray-800 truncate">
                  {note.title ?? "Untitled"}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      note.embedded
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {note.embedded ? "indexed" : "not indexed"}
                  </span>
                  <button
                    onClick={() => handleDelete(note)}
                    disabled={deleting.has(note.id)}
                    title="Delete note"
                    className="text-red-400 hover:text-red-600 disabled:opacity-40 transition-colors"
                  >
                    {deleting.has(note.id) ? (
                      <span className="inline-block w-4 h-4 border-2 border-red-300 border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <TrashIcon />
                    )}
                  </button>
                </div>
              </div>
              <p className="mt-1 text-xs text-gray-500 line-clamp-2 leading-relaxed">
                {note.content_preview}
              </p>
              <p className="mt-2 text-xs text-gray-300">{formatDate(note.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
