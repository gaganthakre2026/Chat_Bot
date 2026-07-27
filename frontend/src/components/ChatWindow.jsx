import { ChevronDown, FileText, Loader2, Send, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { sendMessage } from "../api/client.js";
import MessageBubble from "./MessageBubble.jsx";

export default function ChatWindow({
  document,
  documents,
  onSelectDocument,
  messages,
  setMessages,
  token,
  sessionId,
  onSessionId,
  loadingHistory,
}) {
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  const canChat = document?.status === "ready" && !sending;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || !document || !canChat) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      retrieved_chunks: [],
      confidence: null,
    };

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setSending(true);
    setError("");

    try {
      const response = await sendMessage(document.id, trimmed, sessionId, token);
      onSessionId(response.session_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          retrieved_chunks: response.retrieved_chunks,
          confidence: response.confidence,
          grounded: response.grounded,
        },
      ]);
    } catch (sendError) {
      setError(sendError.message);
    } finally {
      setSending(false);
    }
  }

  if (!document) {
    return (
      <section className="flex min-h-0 flex-1 flex-col items-center justify-center p-8 text-center">
        <div className="max-w-md rounded-3xl border border-dashed border-indigo-200 bg-white/80 px-8 py-10 shadow-subtle">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-600">
            <FileText size={28} />
          </div>
          <h2 className="mt-5 text-xl font-bold text-slate-900">No document selected</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Upload a PDF using the button at the top, then select it to start chatting. Answers
            will use only the content from your uploaded file.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-slate-200/80 bg-white/70 px-4 py-3 backdrop-blur-sm">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-3">
          <label className="min-w-0 flex-1">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Active document
            </span>
            <div className="relative">
              <select
                value={document.id}
                onChange={(event) => onSelectDocument(event.target.value)}
                className="h-11 w-full appearance-none rounded-xl border border-slate-200 bg-white pl-4 pr-10 text-sm font-medium text-slate-800 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
              >
                {documents.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.filename} ({item.status})
                  </option>
                ))}
              </select>
              <ChevronDown
                size={16}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
            </div>
          </label>

          <div className="rounded-xl bg-slate-50 px-4 py-2 ring-1 ring-slate-200">
            <p className="text-xs text-slate-500">Status</p>
            <p className="text-sm font-semibold capitalize text-slate-800">
              {document.status}
              {document.status === "processing" && typeof document.chunk_count === "number"
                ? ` · ${document.chunk_count} chunks indexed`
                : ""}
            </p>
          </div>
        </div>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-4xl space-y-5">
          {loadingHistory ? (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
              <Loader2 size={18} className="animate-spin" />
              Loading conversation
            </div>
          ) : messages.length ? (
            messages.map((message) => <MessageBubble key={message.id} message={message} />)
          ) : (
            <div className="rounded-3xl border border-slate-200 bg-white px-6 py-8 text-center shadow-sm">
              <Sparkles className="mx-auto text-indigo-500" size={28} />
              <h3 className="mt-4 text-lg font-semibold text-slate-900">
                Ask anything about &ldquo;{document.filename}&rdquo;
              </h3>
              <p className="mt-2 text-sm text-slate-500">
                Responses are generated strictly from your PDF. If the answer is not in the
                document, you will see: &ldquo;I don&apos;t have information about that.&rdquo;
              </p>
            </div>
          )}

          {sending ? (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 size={16} className="animate-spin" />
              Searching your document and generating answer...
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>
      </div>

      <form
        className="border-t border-slate-200 bg-white/90 px-4 py-4 backdrop-blur-sm"
        onSubmit={handleSubmit}
      >
        <div className="mx-auto max-w-4xl">
          {document.status !== "ready" ? (
            <p className="mb-3 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800 ring-1 ring-amber-100">
              Document is <strong>{document.status}</strong>. Chat unlocks when indexing is complete.
            </p>
          ) : null}
          {error ? (
            <p className="mb-3 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-rose-100">
              {error}
            </p>
          ) : null}
          <div className="flex items-end gap-3 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-100">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={2}
              className="min-h-[52px] flex-1 resize-none border-0 bg-transparent px-3 py-2 text-sm leading-6 outline-none"
              placeholder={
                document.status === "ready"
                  ? "Ask a question about your PDF..."
                  : "Waiting for document to be ready..."
              }
              disabled={!document || document.status !== "ready" || sending}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  handleSubmit(event);
                }
              }}
            />
            <button
              type="submit"
              disabled={!question.trim() || !canChat}
              className="mb-1 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
              title="Send message"
            >
              <Send size={18} />
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-slate-400">
            Answers are based only on your uploaded PDF · Confidence score shown on each reply
          </p>
        </div>
      </form>
    </section>
  );
}
