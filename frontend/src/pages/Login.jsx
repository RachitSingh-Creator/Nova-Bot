import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, setTokens } from "../services/api";

function getErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "string" && first.trim()) return first;
    if (first && typeof first === "object") {
      if (typeof first.msg === "string" && first.msg.trim()) return first.msg;
      try {
        return JSON.stringify(first);
      } catch {
        return fallback;
      }
    }
  }

  return fallback;
}

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const data = await login({ email, password });
      setTokens(data.access_token, data.refresh_token);
      navigate("/");
    } catch (err) {
      setError(getErrorMessage(err, "Login failed"));
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-gradient-to-br from-slate-100 to-cyan-100 dark:from-slate-950 dark:to-slate-900 p-4 text-slate-900 dark:text-slate-100">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-2xl bg-white/90 dark:bg-slate-900/90 p-6 shadow-xl border border-slate-200/70 dark:border-slate-700">
        <h1 className="text-3xl font-bold mb-1 text-slate-900 dark:text-slate-50">Nova Bot</h1>
        <p className="text-base text-slate-700 dark:text-slate-300 mb-4">Login</p>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Email" className="mb-3 w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 bg-white/80 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" className="mb-3 w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 bg-white/80 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400" />
        {error && <p className="text-sm text-rose-600 mb-2">{error}</p>}
        <button className="w-full rounded-lg bg-sky-600 hover:bg-sky-500 text-white py-2">Login</button>
        <button type="button" onClick={() => navigate("/signup")} className="w-full mt-2 text-sm text-sky-700 dark:text-sky-300 hover:underline">Create account</button>
      </form>
    </div>
  );
}
