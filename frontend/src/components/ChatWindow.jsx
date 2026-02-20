import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function ChatWindow({ messages, isStreaming }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
  }, [messages, isStreaming]);

  return (
    <div className="flex-1 overflow-auto px-4 py-4 space-y-4">
      {messages.length === 0 ? (
        <div className="animate-pulse rounded-2xl border border-dashed border-slate-300 dark:border-slate-600 p-8 text-center opacity-70">
          Start a conversation with Nova Bot.
        </div>
      ) : (
        messages.map((msg) => (
          <div key={msg.localId || msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <MessageBubble role={msg.role} content={msg.content} loading={msg.loading} onCopy={() => navigator.clipboard.writeText(msg.content || "")} />
          </div>
        ))
      )}
      {isStreaming && (
        <div className="flex justify-start">
          <MessageBubble role="assistant" content="" loading />
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
