import { Edit2, Plus, Trash2 } from "lucide-react";

export default function Sidebar({ chats, activeId, onCreate, onSelect, onRename, onDelete }) {
  return (
    <aside className="w-full md:w-72 border-r border-slate-200 dark:border-slate-700 bg-slate-100/70 dark:bg-slate-900/40 p-3">
      <button onClick={onCreate} className="w-full flex items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 py-2 text-white hover:bg-sky-500">
        <Plus size={16} /> New Chat
      </button>
      <div className="mt-4 space-y-2 max-h-[70vh] overflow-auto pr-1">
        {chats.map((chat) => (
          <div key={chat.id} className={`rounded-xl p-2 border ${activeId === chat.id ? "bg-sky-100 text-slate-900 border-sky-200 dark:bg-sky-900/40 dark:text-slate-100 dark:border-sky-800/60" : "bg-white text-slate-900 border-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-700"}`}>
            <button onClick={() => onSelect(chat.id)} className="w-full text-left text-sm font-medium truncate">
              {chat.title}
            </button>
            <div className="mt-1 flex justify-end gap-2">
              <button onClick={() => onRename(chat)} className="text-xs text-slate-600 dark:text-slate-300 opacity-80 hover:opacity-100"><Edit2 size={14} /></button>
              <button onClick={() => onDelete(chat.id)} className="text-xs text-slate-600 dark:text-slate-300 opacity-80 hover:opacity-100"><Trash2 size={14} /></button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
