import { AlertCircle, Bot, UserRound } from "lucide-react";
import ConfidenceBadge from "./ConfidenceBadge.jsx";
import SourcesPanel from "./SourcesPanel.jsx";
import { formatAssistantAnswer, isNotFoundAnswer } from "../lib/messages.js";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const content = isUser ? message.content : formatAssistantAnswer(message.content);
  const notFound = !isUser && isNotFoundAnswer(message.content);

  return (
    <div className={`fade-in flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
          isUser
            ? "bg-indigo-600 text-white"
            : notFound
              ? "bg-amber-100 text-amber-700"
              : "bg-slate-100 text-slate-600"
        }`}
      >
        {isUser ? <UserRound size={18} /> : notFound ? <AlertCircle size={18} /> : <Bot size={18} />}
      </div>

      <article
        className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm md:max-w-[75%] ${
          isUser
            ? "rounded-tr-md bg-indigo-600 text-white"
            : notFound
              ? "rounded-tl-md border border-amber-200 bg-amber-50 text-amber-950"
              : "rounded-tl-md border border-slate-200 bg-white text-slate-900"
        }`}
      >
        {!isUser && !notFound ? (
          <div className="mb-3">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        ) : null}

        {notFound ? (
          <p className="text-sm font-medium leading-6">{content}</p>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-7">{content}</p>
        )}

        {!isUser && !notFound ? <SourcesPanel chunks={message.retrieved_chunks} /> : null}

        {!isUser && notFound ? (
          <p className="mt-2 text-xs text-amber-700/80">
            This answer is based only on your uploaded PDF. Try rephrasing or ask about content in
            the document.
          </p>
        ) : null}
      </article>
    </div>
  );
}
