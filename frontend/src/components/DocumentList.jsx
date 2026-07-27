import { FileText, Loader2, RefreshCcw, Trash2 } from "lucide-react";

function statusClass(status) {
  if (status === "ready") return "bg-emerald-100 text-emerald-700";
  if (status === "failed") return "bg-rose-100 text-rose-700";
  return "bg-amber-100 text-amber-700";
}

export default function DocumentList({
  documents,
  selectedId,
  loading,
  onSelect,
  onDelete,
  onRefresh,
}) {
  return (
    <section className="flex h-full min-h-0 flex-col">
      <div className="flex h-14 items-center justify-between border-b border-slate-100 px-4">
        <h2 className="text-sm font-bold text-slate-800">Your PDFs</h2>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
          title="Refresh"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCcw size={16} />}
        </button>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-3">
        {documents.length ? (
          <div className="space-y-2">
            {documents.map((document) => (
              <div
                key={document.id}
                className={`group rounded-xl border p-3 transition ${
                  selectedId === document.id
                    ? "border-indigo-300 bg-indigo-50/50 ring-2 ring-indigo-100"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelect(document.id)}
                  className="flex w-full items-start gap-3 text-left"
                >
                  <FileText
                    size={18}
                    className={`mt-0.5 shrink-0 ${
                      selectedId === document.id ? "text-indigo-600" : "text-slate-400"
                    }`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {document.filename}
                    </span>
                    <span className="mt-2 flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase ${statusClass(document.status)}`}
                      >
                        {document.status}
                      </span>
                      <span className="text-xs text-slate-500">{document.page_count || 0} pages</span>
                      {typeof document.chunk_count === "number" ? (
                        <span className="text-xs text-slate-500">{document.chunk_count} chunks</span>
                      ) : null}
                    </span>
                  </span>
                </button>
                <div className="mt-2 flex justify-end opacity-0 transition group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={() => onDelete(document.id)}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                    title="Delete"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-500">
            No PDFs yet. Use <strong>Upload PDF</strong> at the top.
          </div>
        )}
      </div>
    </section>
  );
}
