"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth, UserButton, useUser } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertCircle, ArrowUpRight, Check, Clock3, FileText, HeartPulse, Menu, MessageCircle, Moon, Plus, Search, Settings2, ShieldCheck, Sparkles, Sun, Trash2, X } from "lucide-react";
import { api, type Chat } from "@/lib/api";
import { useUIStore } from "@/store/ui";
import { AIChatPanel } from "@/components/ai-chat-panel";

type SettingsTab = "Profile" | "Preferences" | "Privacy" | "Language";
type LanguageMode = "auto" | "english" | "kannada";

export function Dashboard() {
  const { getToken, isLoaded, isSignedIn, userId } = useAuth();
  const { user } = useUser();
  const qc = useQueryClient();
  const [active, setActive] = useState<string | null>(null);
  const [dark, setDark] = useState(false);
  const [fontSize, setFontSize] = useState("16");
  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [actionError, setActionError] = useState("");
  const [greeting, setGreeting] = useState("Hello");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("Profile");
  const [languageMode, setLanguageMode] = useState<LanguageMode>("auto");
  const [initialPrompt, setInitialPrompt] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsMessage, setSettingsMessage] = useState("");
  const query = useUIStore(s => s.query);
  const setQuery = useUIStore(s => s.setQuery);
  const authReady = isLoaded && isSignedIn;
  const chats = useQuery({ queryKey: ["chats", userId], enabled: authReady, queryFn: async () => api<Chat[]>("/chats", (await getToken()) ?? "") });
  const createChat = useMutation({
    mutationFn: async (prompt?: string) => api<Chat>("/chats", (await getToken()) ?? "", { method: "POST", body: JSON.stringify({ title: prompt?.trim().slice(0, 80) || "New conversation" }) }),
    onSuccess: async (chat, prompt) => { await qc.invalidateQueries({ queryKey: ["chats"] }); setActive(chat.id); setInitialPrompt(prompt ?? ""); setSidebarOpen(false); setActionError(""); },
    onError: (reason: Error) => setActionError(reason.message || "Could not create a conversation."),
  });
  const deleteChat = useMutation({
    mutationFn: async (id: string) => api<void>(`/chats/${id}`, (await getToken()) ?? "", { method: "DELETE" }),
    onSuccess: async (_, id) => { setActive(current => current === id ? null : current); await qc.invalidateQueries({ queryKey: ["chats"] }); },
    onError: (reason: Error) => setActionError(reason.message || "Could not delete this conversation."),
  });
  const renameChat = useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) => api<Chat>(`/chats/${id}`, (await getToken()) ?? "", { method: "PATCH", body: JSON.stringify({ title: name }) }),
    onSuccess: async () => { setRenaming(null); await qc.invalidateQueries({ queryKey: ["chats"] }); },
    onError: (reason: Error) => setActionError(reason.message || "Could not rename this conversation."),
  });
  const filtered = useMemo(() => chats.data?.filter(chat => chat.title.toLowerCase().includes(query.toLowerCase())) ?? [], [chats.data, query]);
  const groups = useMemo(() => groupChats(filtered), [filtered]);
  const initials = user?.fullName?.split(" ").map(part => part[0]).join("").slice(0, 2) || "MA";

  useEffect(() => {
    const savedTheme = localStorage.getItem("medassist-theme");
    const savedSize = localStorage.getItem("medassist-font-size");
    if (savedTheme) setDark(savedTheme === "dark");
    if (savedSize && ["14", "16", "18"].includes(savedSize)) setFontSize(savedSize);
    setGreeting(new Date().getHours() < 12 ? "Good morning" : new Date().getHours() < 17 ? "Good afternoon" : "Good evening");
    setPreferencesLoaded(true);
  }, []);
  useEffect(() => { document.documentElement.classList.toggle("dark", dark); if (preferencesLoaded) localStorage.setItem("medassist-theme", dark ? "dark" : "light"); }, [dark, preferencesLoaded]);
  useEffect(() => { document.documentElement.style.fontSize = `${fontSize}px`; if (preferencesLoaded) localStorage.setItem("medassist-font-size", fontSize); }, [fontSize, preferencesLoaded]);
  useEffect(() => {
    if (!settingsOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setSettingsOpen(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [settingsOpen]);
  useEffect(() => {
    const onShortcut = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); startChat(); }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [authReady, createChat.isPending]);
  useEffect(() => {
    if (!settingsOpen || settingsTab !== "Language" || !active) return;
    let alive = true;
    void (async () => {
      try { const memory = await api<{ language_mode: string }>(`/memory/session/${active}`, (await getToken()) ?? ""); if (alive && ["auto", "english", "kannada"].includes(memory.language_mode)) setLanguageMode(memory.language_mode as LanguageMode); }
      catch { if (alive) setSettingsMessage("Could not load this conversation’s language preference."); }
    })();
    return () => { alive = false; };
  }, [settingsOpen, settingsTab, active, getToken]);

  function startChat(prompt?: string) { if (!authReady || createChat.isPending) return; setActionError(""); createChat.mutate(prompt); }
  function saveRename(id: string) { const name = title.trim(); if (!name || renameChat.isPending) return; renameChat.mutate({ id, name }); }
  async function saveLanguage(mode: LanguageMode) {
    setLanguageMode(mode); setSettingsMessage("");
    if (!active) { setSettingsMessage("Open a conversation to save its language preference."); return; }
    try { await api("/ai/language-mode", (await getToken()) ?? "", { method: "POST", body: JSON.stringify({ session_id: active, mode }) }); await qc.invalidateQueries({ queryKey: ["session-memory", active] }); setSettingsMessage("Language preference saved for this conversation."); }
    catch (reason) { setSettingsMessage(reason instanceof Error ? reason.message : "Could not save this preference."); }
  }
  const toggleTheme = () => setDark(value => !value);

  return <main className={`flex h-dvh overflow-hidden ${dark ? "bg-[#111a28] text-slate-100" : "bg-[#f7faff] text-[#15243a]"}`}>
    {sidebarOpen && <><button aria-label="Close navigation" onClick={() => setSidebarOpen(false)} className="fixed inset-0 z-30 bg-slate-950/35 md:hidden"/><aside className={`fixed inset-y-0 left-0 z-40 flex w-[292px] flex-col border-r transition-transform md:relative md:z-10 md:translate-x-0 ${dark ? "border-slate-700 bg-[#151f2e]" : "border-[#e8edf4] bg-white"}`}>
      <div className="flex h-16 shrink-0 items-center gap-3 px-5"><div className="grid h-9 w-9 place-items-center rounded-xl bg-blue-600 text-lg font-bold text-white shadow-sm shadow-blue-200">M</div><div><div className="font-semibold tracking-tight">MedAssist <span className="text-blue-600">AI</span></div><div className="text-[10px] font-medium uppercase tracking-[.17em] text-slate-400">Care workspace</div></div><button type="button" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar" className="ml-auto rounded-lg p-2 text-slate-400 hover:bg-slate-100 md:hidden"><X size={16}/></button></div>
      <div className="px-4 pt-3"><button type="button" onClick={() => startChat()} disabled={!authReady || createChat.isPending} className="flex h-11 w-full items-center gap-2 rounded-xl bg-blue-600 px-3 text-sm font-semibold text-white shadow-md shadow-blue-200/60 transition hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60"><Plus size={17}/>{createChat.isPending ? "Creating…" : "New conversation"}<span className="ml-auto rounded border border-white/25 px-1.5 py-0.5 text-[10px] text-blue-100">Ctrl K</span></button></div>
      <div className="px-4 pb-2 pt-5"><label htmlFor="chat-search" className="sr-only">Search conversations</label><div className="relative"><Search size={14} className="absolute left-3 top-2.5 text-slate-400"/><input id="chat-search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search conversations" className="h-9 w-full rounded-lg border border-slate-100 bg-slate-50 pl-9 pr-3 text-xs outline-none transition focus:border-blue-200 focus:bg-white"/></div></div>
      <nav aria-label="Chat history" className="soft-scroll flex-1 space-y-4 overflow-y-auto px-3 py-2">{!isLoaded || chats.isLoading ? <p role="status" className="px-3 py-5 text-xs text-slate-400">Loading history…</p> : chats.error ? <p role="alert" className="px-3 py-5 text-xs text-rose-600">Could not load chat history. <button type="button" onClick={() => void chats.refetch()} className="underline">Retry</button></p> : groups.length ? groups.map(group => <section key={group.label}><h2 className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-[.14em] text-slate-400">{group.label}</h2><div className="space-y-0.5">{group.chats.map(chat => <div key={chat.id} className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 transition ${active === chat.id ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"}`}>
        {renaming === chat.id ? <input autoFocus aria-label={`Rename ${chat.title}`} value={title} onChange={event => setTitle(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); saveRename(chat.id); } if (event.key === "Escape") setRenaming(null); }} className="min-w-0 flex-1 rounded border px-2 py-1 text-xs"/> : <button type="button" onClick={() => { setActive(chat.id); setInitialPrompt(""); setSidebarOpen(false); }} className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-1.5 py-1 text-left text-xs"><MessageCircle size={14} className="shrink-0 opacity-70"/><span className="truncate">{chat.title}</span></button>}
        <details className="relative"><summary aria-label={`Actions for ${chat.title}`} className="list-none cursor-pointer rounded-md p-1 text-slate-400 opacity-70 hover:bg-white hover:text-slate-700 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100"><span className="sr-only">Chat actions</span><MoreIcon/></summary><div className="absolute right-0 top-7 z-20 w-36 rounded-xl border border-slate-200 bg-white p-1 shadow-lg"><button type="button" onClick={() => { setRenaming(chat.id); setTitle(chat.title); }} className="w-full rounded-lg px-2.5 py-2 text-left text-xs text-slate-700 hover:bg-slate-50">Rename</button><button type="button" disabled={deleteChat.isPending} onClick={() => { if (window.confirm("Delete this conversation and its reports?")) deleteChat.mutate(chat.id); }} className="w-full rounded-lg px-2.5 py-2 text-left text-xs text-rose-600 hover:bg-rose-50">Delete</button></div></details>
      </div>)}</div></section>) : <p className="px-3 py-5 text-center text-xs text-slate-400">{query ? "No matching conversations" : "Your conversations will appear here"}</p>}</nav>
      <div className="mx-4 mb-3 rounded-xl border border-blue-100 bg-blue-50/60 p-3"><div className="mb-1.5 flex items-center gap-2 text-blue-700"><ShieldCheck size={15}/><span className="text-xs font-semibold">Private by design</span></div><p className="text-[10px] leading-relaxed text-slate-500">Conversations and reports stay linked to your account.</p></div>
      <div className="border-t border-slate-100 p-3"><button type="button" onClick={() => { setSettingsTab("Profile"); setSettingsMessage(""); setSettingsOpen(true); setSidebarOpen(false); }} className="mb-1 flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-xs text-slate-600 hover:bg-slate-50"><Settings2 size={16} className="text-slate-400"/>Settings</button><div className="flex items-center gap-2 rounded-xl p-2"><div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-blue-100 text-[11px] font-semibold text-blue-700">{initials}</div><div className="min-w-0 flex-1"><div className="truncate text-xs font-semibold">{user?.fullName ?? "Your account"}</div><div className="truncate text-[10px] text-slate-400">{user?.primaryEmailAddress?.emailAddress}</div></div><UserButton afterSignOutUrl="/sign-in" userProfileProps={{ apiKeysProps: { hide: true } }}/></div></div>
    </aside></>}
    <section className="flex min-w-0 flex-1 flex-col">
      <header className={`z-10 flex h-14 shrink-0 items-center justify-between border-b px-3 sm:px-5 md:px-8 ${dark ? "border-slate-700 bg-[#111a28]" : "border-[#e8edf4] bg-white/90 backdrop-blur"}`}><div className="flex min-w-0 items-center gap-2.5">{!sidebarOpen && <button type="button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar" className="rounded-lg p-2 hover:bg-slate-100"><Menu size={18}/></button>}<div className="truncate text-sm font-medium text-slate-700">{active ? chats.data?.find(chat => chat.id === active)?.title ?? "Conversation" : "MedAssist AI"}</div></div><div className="flex items-center gap-1.5"><div className="relative hidden sm:block"><Search size={14} className="absolute left-3 top-2.5 text-slate-400"/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search chats" aria-label="Search chats" className="h-9 w-44 rounded-lg border border-slate-100 bg-slate-50 pl-9 pr-3 text-xs outline-none focus:border-blue-200 focus:bg-white"/></div><button type="button" onClick={toggleTheme} aria-label="Toggle theme" title="Toggle theme" className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100">{dark ? <Sun size={17}/> : <Moon size={17}/>}</button><UserButton afterSignOutUrl="/sign-in" userProfileProps={{ apiKeysProps: { hide: true } }}/></div></header>
      {actionError && <div role="alert" className="mx-4 mt-3 flex items-center gap-2 rounded-xl border border-rose-100 bg-rose-50 px-3 py-2.5 text-xs text-rose-700 sm:mx-8"><AlertCircle size={15}/><span>{actionError}</span><button type="button" onClick={() => setActionError("")} aria-label="Dismiss error" className="ml-auto rounded p-1 hover:bg-rose-100"><X size={14}/></button></div>}
      {active ? <div className="flex min-h-0 flex-1 overflow-hidden"><div className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col px-3 pb-2 pt-3 sm:px-6 md:px-10 md:pt-5"><AIChatPanel key={active} sessionId={active} title={chats.data?.find(chat => chat.id === active)?.title ?? "Conversation"} initialPrompt={initialPrompt} onDelete={() => deleteChat.mutate(active)} getToken={getToken}/></div></div> : <div className="soft-scroll flex-1 overflow-y-auto"><div className="mx-auto flex min-h-full max-w-4xl flex-col justify-center px-5 py-10 sm:px-8"><div className="mb-5 flex items-center gap-2"><span className="inline-flex items-center gap-1.5 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-[11px] font-medium text-blue-700"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500"/>Your private care space</span><span className="hidden text-xs text-slate-400 sm:inline"><Clock3 size={12} className="mr-1 inline"/>Ready when you are</span></div><h1 className="max-w-2xl text-3xl font-semibold leading-tight tracking-[-.04em] sm:text-4xl">{greeting}{user?.firstName ? `, ${user.firstName}` : ""}.<br/><span className="text-blue-600">How can I help with your health today?</span></h1><p className="mt-4 max-w-xl text-sm leading-6 text-slate-500">Start with a general health question. Add a report anytime for answers grounded in your document.</p><div className="mt-7 grid max-w-2xl gap-2 sm:grid-cols-2">{["Summarize a medical report", "Explain a diagnosis", "Find a specialist", "Understand lab results"].map(prompt => <button type="button" key={prompt} onClick={() => startChat(prompt)} disabled={!authReady || createChat.isPending} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3.5 text-left text-xs font-medium text-slate-600 transition hover:border-blue-200 hover:bg-blue-50/40 disabled:opacity-50"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-600"><Sparkles size={15}/></span>{prompt}<ArrowUpRight size={14} className="ml-auto text-slate-300"/></button>)}</div><button type="button" onClick={() => startChat()} disabled={!authReady || createChat.isPending} className="mt-6 inline-flex h-11 w-fit items-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-50"><Plus size={16}/>{createChat.isPending ? "Creating conversation…" : "Start a conversation"}</button><div className="mt-10 flex flex-wrap gap-3 text-[10px] text-slate-400"><span className="inline-flex items-center gap-1.5"><ShieldCheck size={13} className="text-blue-500"/>Private to your account</span><span className="inline-flex items-center gap-1.5"><HeartPulse size={13} className="text-blue-500"/>Not a substitute for professional medical advice</span></div><div className="mt-9 grid gap-3 sm:grid-cols-3"><Stat icon={<MessageCircle size={16}/>} label="Conversations" value={String(chats.data?.length ?? 0)} note="Your saved chats"/><Stat icon={<Activity size={16}/>} label="Workspace" value="Ready" note="Your space is set up"/><Stat icon={<ShieldCheck size={16}/>} label="Privacy" value="Protected" note="Personal to your account"/></div></div></div>}
    </section>
    {settingsOpen && <div role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setSettingsOpen(false); }} className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-3 backdrop-blur-sm sm:p-6"><section role="dialog" aria-modal="true" aria-labelledby="settings-title" className="flex max-h-[90dvh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"><header className="flex items-center justify-between border-b px-5 py-4"><div><h2 id="settings-title" className="text-base font-semibold">Settings</h2><p className="mt-1 text-xs text-slate-500">Manage your profile and workspace preferences.</p></div><button type="button" onClick={() => setSettingsOpen(false)} aria-label="Close settings" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X size={17}/></button></header><div className="flex min-h-0 flex-1 flex-col sm:flex-row"><nav aria-label="Settings sections" className="flex shrink-0 gap-1 overflow-x-auto border-b p-2 sm:w-40 sm:flex-col sm:border-b-0 sm:border-r">{(["Profile", "Preferences", "Privacy", "Language"] as SettingsTab[]).map(tab => <button type="button" key={tab} onClick={() => { setSettingsTab(tab); setSettingsMessage(""); }} aria-current={settingsTab === tab ? "page" : undefined} className={`rounded-lg px-3 py-2 text-left text-xs ${settingsTab === tab ? "bg-blue-50 font-semibold text-blue-700" : "text-slate-500 hover:bg-slate-50"}`}>{tab}</button>)}</nav><div className="soft-scroll flex-1 overflow-y-auto p-5">{settingsTab === "Profile" && <div className="space-y-4"><h3 className="text-sm font-semibold">Profile</h3><SettingField label="Name" value={user?.fullName || "Not provided"}/><SettingField label="Email" value={user?.primaryEmailAddress?.emailAddress || "Not provided"}/><p className="text-[11px] leading-5 text-slate-400">Update your profile details using your secure account menu.</p></div>}{settingsTab === "Preferences" && <div className="space-y-5"><h3 className="text-sm font-semibold">Preferences</h3><label className="block text-xs font-medium text-slate-600">Theme<select value={dark ? "dark" : "light"} onChange={event => setDark(event.target.value === "dark")} className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"><option value="light">Light</option><option value="dark">Dark</option></select></label><label className="block text-xs font-medium text-slate-600">Font size<select value={fontSize} onChange={event => setFontSize(event.target.value)} className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm"><option value="14">Small</option><option value="16">Default</option><option value="18">Large</option></select></label></div>}{settingsTab === "Language" && <div className="space-y-4"><h3 className="text-sm font-semibold">Conversation language</h3><p className="text-xs leading-5 text-slate-500">Language is saved per conversation and applies to future responses in that chat.</p><label className="block text-xs font-medium text-slate-600">Response language<select disabled={!active} value={languageMode} onChange={event => void saveLanguage(event.target.value as LanguageMode)} className="mt-2 h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm disabled:bg-slate-50"><option value="auto">Auto</option><option value="english">English</option><option value="kannada">Kannada</option></select></label>{!active && <p className="text-[11px] text-slate-400">Open a conversation before setting its language.</p>}</div>}{settingsTab === "Privacy" && <div className="space-y-3"><h3 className="text-sm font-semibold">Privacy and data handling</h3><div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4 text-xs leading-6 text-slate-600">Your chats and uploaded reports are associated with your signed-in account. Reports are processed to extract text and provide document-grounded answers. Use the chat and report delete controls to remove stored items. Avoid sharing information you do not want processed.</div><p className="text-[11px] text-slate-400">Generated health information is informational and does not replace professional care.</p></div>}{settingsMessage && <p role="status" className="mt-4 text-xs text-blue-700">{settingsMessage}</p>}</div></div><footer className="flex justify-end border-t px-5 py-3"><button type="button" onClick={() => setSettingsOpen(false)} className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700">Done</button></footer></section></div>}
  </main>;
}

function groupChats(chats: Chat[]) {
  const now = new Date(); const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime(); const yesterday = today - 86_400_000; const week = today - 7 * 86_400_000;
  const groups = new Map<string, Chat[]>();
  for (const chat of chats) {
    const time = new Date(chat.updated_at).getTime();
    const key = time >= today ? "Recent" : time >= yesterday ? "Yesterday" : time >= week ? "Previous 7 Days" : "Earlier";
    groups.set(key, [...(groups.get(key) ?? []), chat]);
  }
  return [...groups].map(([label, values]) => ({ label, chats: values }));
}

function MoreIcon() { return <span className="block text-base leading-none" aria-hidden="true">···</span>; }
function SettingField({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-slate-200 px-3.5 py-3"><div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</div><div className="mt-1.5 text-sm text-slate-700">{value}</div></div>; }
function Stat({ icon, label, value, note }: { icon: React.ReactNode; label: string; value: string; note: string }) { return <div className="rounded-xl border border-[#e8edf4] bg-white p-4"><div className="mb-3 flex items-center justify-between"><span className="text-xs text-slate-500">{label}</span><span className="text-blue-500">{icon}</span></div><div className="text-lg font-semibold tracking-tight">{value}</div><div className="mt-1 text-[10px] text-slate-400">{note}</div></div>; }
