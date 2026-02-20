import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageBubble({ role, content, loading, onCopy }) {
  const bubbleClass = useMemo(
    () =>
      role === "user"
        ? "bg-sky-600 text-white ml-auto"
        : "bg-white/80 dark:bg-slate-800/90 text-slate-900 dark:text-slate-100 mr-auto border border-slate-200 dark:border-slate-700",
    [role]
  );

  return (
    <div className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${bubbleClass}`}>
      {loading ? (
        <div className="flex gap-2 py-2">
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:120ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:240ms]" />
        </div>
      ) : (
        <>
          <div className="prose prose-sm max-w-none dark:prose-invert prose-pre:bg-slate-900 prose-pre:text-slate-100">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content || ""}</ReactMarkdown>
          </div>
          <button onClick={onCopy} className="mt-2 text-xs opacity-70 hover:opacity-100">
            Copy
          </button>
        </>
      )}
    </div>
  );
}
