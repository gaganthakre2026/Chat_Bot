import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { useState } from "react";

export default function SourcesPanel({ chunks = [] }) {
  const [open, setOpen] = useState(false);

  if (!chunks.length) return null;

  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-8 items-center gap-2 rounded-lg px-2 text-xs font-semibold uppercase tracking-wide text-indigo-600 hover:bg-indigo-50"
        title="Show source chunks from PDF"
      >
        <FileText size={14} />
        Sources from PDF
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open ? (
        <div className="mt-2 space-y-2">
          {chunks.map((chunk, index) => (
            <div
              key={`${chunk.page}-${index}`}
              className="rounded-xl border border-slate-100 bg-slate-50 p-3"
            >
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
                <span>Page {chunk.page || "?"}</span>
                <span>·</span>
                <span>Match {Math.round(Number(chunk.score || 0) * 100)}%</span>
              </div>
              <p className="text-sm leading-6 text-slate-700">{chunk.text}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
