export default function Navbar({ user, theme, onToggleTheme, model, onModelChange, usage, onLogout }) {
  return (
    <header className="border-b border-slate-200 dark:border-slate-700 px-4 py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between text-slate-900 dark:text-slate-100">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Nova Bot</h1>
        <p className="text-xs text-slate-600 dark:text-slate-300">{user?.email}</p>
      </div>
      <div className="flex items-center gap-2">
        <select
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
          className="rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-2 py-1 text-sm"
        >
          <optgroup label="OpenAI">
            <option value="gpt-4o-mini">gpt-4o-mini</option>
            <option value="gpt-4o">gpt-4o</option>
          </optgroup>
          <optgroup label="Gemini">
            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
          </optgroup>
        </select>
        <span className="text-xs text-slate-600 dark:text-slate-300">Tokens: {usage?.total_tokens ?? 0}</span>
        <button onClick={onToggleTheme} className="rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-2 py-1 text-sm">{theme === "dark" ? "Light" : "Dark"}</button>
        <button onClick={onLogout} className="rounded-lg bg-rose-600 px-2 py-1 text-sm text-white">Logout</button>
      </div>
    </header>
  );
}
