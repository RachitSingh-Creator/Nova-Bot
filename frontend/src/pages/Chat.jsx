import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ChatWindow from "../components/ChatWindow";
import Navbar from "../components/Navbar";
import Sidebar from "../components/Sidebar";
import useTheme from "../hooks/useTheme";
import {
  clearTokens,
  createChat,
  deleteChat,
  fetchHistory,
  fetchMe,
  fetchUsage,
  getAccessToken,
  listChats,
  renameChat,
  sendChat,
  streamChat,
} from "../services/api";

export default function Chat() {
  const DEFAULT_SYSTEM_PROMPT = "I am Nova Bot, your helpful AI assistant.";
  const LEGACY_SYSTEM_PROMPT = "You are Nova Bot, a helpful AI assistant.";
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const [user, setUser] = useState(null);
  const [usage, setUsage] = useState(null);
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(700);
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT);
  const [isStreaming, setIsStreaming] = useState(false);
  const [actionError, setActionError] = useState("");
  const [isListening, setIsListening] = useState(false);
  const abortRef = useRef(null);
  const speechRef = useRef(null);

  const activeChat = useMemo(() => chats.find((x) => x.id === activeChatId) || null, [chats, activeChatId]);

  useEffect(() => {
    if (!getAccessToken()) {
      navigate("/login");
      return;
    }
    bootstrap();
  }, []);

  useEffect(() => {
    return () => {
      speechRef.current?.stop?.();
    };
  }, []);

  async function bootstrap() {
    try {
      const [me, chatList, usageData] = await Promise.all([fetchMe(), listChats(), fetchUsage()]);
      setUser(me);
      setUsage(usageData);
      setChats(chatList);
      if (chatList.length > 0) {
        await selectChat(chatList[0].id);
      } else {
        await handleNewChat();
      }
    } catch {
      clearTokens();
      navigate("/login");
    }
  }

  async function selectChat(chatId) {
    setActiveChatId(chatId);
    const { conversation, messages: history } = await fetchHistory(chatId);
    setMessages(history);
    const normalizedModel =
      conversation.model === "gemini-1.5-flash" || conversation.model === "gemini-1.5-flash-latest"
        ? "gemini-2.5-flash"
        : conversation.model;
    setModel(normalizedModel);
    setSystemPrompt(conversation.system_prompt === LEGACY_SYSTEM_PROMPT ? DEFAULT_SYSTEM_PROMPT : conversation.system_prompt);
  }

  async function handleNewChat() {
    const created = await createChat({ title: "New Chat", model, system_prompt: systemPrompt });
    setChats((prev) => [created, ...prev]);
    setActiveChatId(created.id);
    setMessages([]);
  }

  function getErrorMessage(err, fallback) {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (err instanceof Error && err.message) return err.message;
    return fallback;
  }

  async function handleRename(chat) {
    const title = window.prompt("Rename chat", chat.title);
    if (!title) return;
    const updated = await renameChat(chat.id, title);
    setChats((prev) => prev.map((x) => (x.id === chat.id ? updated : x)));
  }

  async function handleDelete(chatId) {
    await deleteChat(chatId);
    const next = chats.filter((x) => x.id !== chatId);
    setChats(next);
    if (activeChatId === chatId) {
      if (next.length > 0) {
        await selectChat(next[0].id);
      } else {
        await handleNewChat();
      }
    }
  }

  function stopGeneration() {
    abortRef.current?.abort();
    setIsStreaming(false);
  }

  function toggleMic() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setActionError("Microphone transcription is not supported in this browser.");
      return;
    }

    if (isListening) {
      speechRef.current?.stop?.();
      return;
    }

    setActionError("");
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;

    let finalText = "";

    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event) => {
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0]?.transcript ?? "";
        if (event.results[i].isFinal) {
          finalText += `${transcript} `;
        } else {
          interimText += transcript;
        }
      }
      const spoken = `${finalText}${interimText}`.trim();
      setInput(spoken);
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") {
        setActionError(`Microphone error: ${event.error}`);
      }
    };
    recognition.onend = () => setIsListening(false);

    speechRef.current = recognition;
    recognition.start();
  }

  function handleInputKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  async function handleSend() {
    if (!input.trim() || !activeChatId || isStreaming) return;
    setActionError("");
    const text = input.trim();
    setInput("");
    const userLocalId = `u-${Date.now()}`;
    const assistantLocalId = `a-${Date.now()}`;

    setMessages((prev) => [...prev, { localId: userLocalId, role: "user", content: text }, { localId: assistantLocalId, role: "assistant", content: "" }]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(
        { conversation_id: activeChatId, message: text, model, temperature, max_tokens: maxTokens, system_prompt: systemPrompt },
        (token) => {
          setMessages((prev) => prev.map((m) => (m.localId === assistantLocalId ? { ...m, content: (m.content || "") + token } : m)));
        },
        async () => {
          setIsStreaming(false);
          const refreshed = await fetchHistory(activeChatId);
          setMessages(refreshed.messages);
          const [usageData, chatsData] = await Promise.all([fetchUsage(), listChats()]);
          setUsage(usageData);
          setChats(chatsData);
        },
        (error) => {
          setIsStreaming(false);
          setActionError(error || "Streaming failed.");
          setMessages((prev) => prev.map((m) => (m.localId === assistantLocalId ? { ...m, content: `Error: ${error}` } : m)));
        },
        controller.signal
      );
    } catch (err) {
      setIsStreaming(false);
      setActionError(getErrorMessage(err, "Streaming failed."));
      setMessages((prev) => prev.map((m) => (m.localId === assistantLocalId ? { ...m, content: "Streaming failed." } : m)));
    }
  }

  async function regenerateLast() {
    if (!activeChat || messages.length < 2 || isStreaming) return;
    setActionError("");
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    try {
      await sendChat({ conversation_id: activeChatId, message: lastUser.content, model, temperature, max_tokens: maxTokens, system_prompt: systemPrompt });
      const refreshed = await fetchHistory(activeChatId);
      setMessages(refreshed.messages);
      const [usageData, chatsData] = await Promise.all([fetchUsage(), listChats()]);
      setUsage(usageData);
      setChats(chatsData);
    } catch (err) {
      setActionError(getErrorMessage(err, "Regenerate failed."));
    }
  }

  function logout() {
    clearTokens();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-cyan-50 to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 text-slate-900 dark:text-slate-100">
      <Navbar
        user={user}
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        model={model}
        onModelChange={setModel}
        usage={usage}
        onLogout={logout}
      />
      <div className="flex flex-col md:flex-row h-[calc(100vh-73px)]">
        <Sidebar chats={chats} activeId={activeChatId} onCreate={handleNewChat} onSelect={selectChat} onRename={handleRename} onDelete={handleDelete} />
        <main className="flex-1 flex flex-col">
          <ChatWindow messages={messages} isStreaming={isStreaming} />
          <div className="border-t border-slate-200 dark:border-slate-700 p-3 space-y-2">
            {actionError && <p className="text-sm text-rose-600">{actionError}</p>}
            <div className="flex flex-wrap gap-2">
              <input value={temperature} onChange={(e) => setTemperature(Number(e.target.value))} type="number" min="0" max="2" step="0.1" className="w-28 rounded-lg border border-slate-300 dark:border-slate-600 px-2 py-1 bg-white/90 dark:bg-slate-900/80 text-slate-900 dark:text-slate-100" placeholder="Temp" />
              <input value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} type="number" min="1" max="4000" className="w-32 rounded-lg border border-slate-300 dark:border-slate-600 px-2 py-1 bg-white/90 dark:bg-slate-900/80 text-slate-900 dark:text-slate-100" placeholder="Max tokens" />
              <input value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} className="flex-1 rounded-lg border border-slate-300 dark:border-slate-600 px-2 py-1 bg-white/90 dark:bg-slate-900/80 text-slate-900 dark:text-slate-100" placeholder="System prompt" />
            </div>
            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleInputKeyDown}
                rows={2}
                className="flex-1 resize-none rounded-xl border border-slate-300 dark:border-slate-600 px-3 py-2 bg-white/90 dark:bg-slate-900/80 text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400"
                placeholder="Ask Nova Bot anything..."
              />
              <div className="flex flex-col gap-2">
                <button
                  onClick={toggleMic}
                  aria-label={isListening ? "Stop microphone" : "Start microphone"}
                  title={isListening ? "Stop microphone" : "Start microphone"}
                  className={`rounded-xl px-4 py-2 text-white ${isListening ? "bg-rose-600 hover:bg-rose-500" : "bg-emerald-600 hover:bg-emerald-500"}`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                    <path d="M12 14a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v4a3 3 0 0 0 3 3Z" />
                    <path d="M5 11a1 1 0 1 1 2 0 5 5 0 1 0 10 0 1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V21h2a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h2v-3.07A7 7 0 0 1 5 11Z" />
                  </svg>
                </button>
                <button onClick={handleSend} className="rounded-xl bg-sky-600 hover:bg-sky-500 text-white px-4 py-2">Send</button>
                <button onClick={regenerateLast} className="rounded-xl border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-100 bg-white/90 dark:bg-slate-900/80 px-4 py-2">Regenerate</button>
                <button onClick={stopGeneration} className="rounded-xl border border-rose-500 text-rose-600 px-4 py-2">Stop</button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
