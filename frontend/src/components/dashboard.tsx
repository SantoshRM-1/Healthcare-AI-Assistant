"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import Link from "next/link";
import { useAuth, UserButton, useUser } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Chat } from "@/lib/api";
import { useUIStore } from "@/store/ui";
import { AIChatPanel } from "@/components/ai-chat-panel";

export function Dashboard() {
  const { getToken, isLoaded, isSignedIn, userId } = useAuth();
  const { user } = useUser();
  const qc = useQueryClient();

  const [active, setActive] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [actionError, setActionError] = useState("");
  const [initialPrompt, setInitialPrompt] = useState("");
  const [chatMenuOpen, setChatMenuOpen] = useState<string | null>(null);
  const sessionLinkApplied = useRef(false);
  const createChatInFlight = useRef(false);

  const query = useUIStore((s) => s.query);
  const setQuery = useUIStore((s) => s.setQuery);
  const authReady = isLoaded && isSignedIn;

  const chats = useQuery({
    queryKey: ["chats", userId],
    enabled: authReady,
    queryFn: async () => api<Chat[]>("/chats", (await getToken()) ?? ""),
  });

  const createChat = useMutation({
    mutationFn: async (prompt?: string) =>
      api<Chat>("/chats", (await getToken()) ?? "", {
        method: "POST",
        body: JSON.stringify({ title: prompt?.trim().slice(0, 80) || "New clinical consult" }),
      }),
    onSuccess: async (chat, prompt) => {
      try {
        qc.setQueryData<Chat[]>(["chats", userId], (current) => [chat, ...(current ?? []).filter((item) => item.id !== chat.id)]);
        setActive(chat.id);
        setInitialPrompt(prompt ?? "");
        if (window.matchMedia("(max-width: 767px)").matches) setSidebarOpen(false);
        setActionError("");
        await qc.invalidateQueries({ queryKey: ["chats", userId] });
      } finally {
        createChatInFlight.current = false;
      }
    },
    onError: (reason: Error) => {
      createChatInFlight.current = false;
      setActionError(reason.message || "Could not create a conversation.");
    },
  });

  const deleteChat = useMutation({
    mutationFn: async (id: string) => api<void>(`/chats/${id}`, (await getToken()) ?? "", { method: "DELETE" }),
    onSuccess: async (_, id) => {
      setActive((current) => (current === id ? null : current));
      setChatMenuOpen(null);
      await qc.invalidateQueries({ queryKey: ["chats"] });
    },
    onError: (reason: Error) => setActionError(reason.message || "Could not delete this conversation."),
  });

  const renameChat = useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) =>
      api<Chat>(`/chats/${id}`, (await getToken()) ?? "", {
        method: "PATCH",
        body: JSON.stringify({ title: name }),
      }),
    onSuccess: async () => {
      setRenaming(null);
      setChatMenuOpen(null);
      await qc.invalidateQueries({ queryKey: ["chats"] });
    },
    onError: (reason: Error) => setActionError(reason.message || "Could not rename this conversation."),
  });

  // Filter chats by search query
  const filteredChats = useMemo(
    () => {
      const seen = new Set<string>();
      return (chats.data ?? []).filter((chat) => {
        if (seen.has(chat.id) || !chat.title.toLowerCase().includes(query.toLowerCase())) return false;
        seen.add(chat.id);
        return true;
      });
    },
    [chats.data, query]
  );

  // Auto-select first chat if none selected and chats exist
  useEffect(() => {
    if (!active && chats.data && chats.data.length > 0) {
      setActive(chats.data[0].id);
    }
  }, [chats.data, active]);

  useEffect(() => {
    if (sessionLinkApplied.current || !chats.data) return;
    sessionLinkApplied.current = true;
    const requestedSessionId = new URLSearchParams(window.location.search).get("session_id");
    if (requestedSessionId && chats.data.some((chat) => chat.id === requestedSessionId)) {
      setActive(requestedSessionId);
      setInitialPrompt("");
    }
  }, [chats.data]);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const syncSidebar = () => setSidebarOpen(!media.matches);
    syncSidebar();
    media.addEventListener("change", syncSidebar);
    return () => media.removeEventListener("change", syncSidebar);
  }, []);

  // Keyboard shortcut Ctrl+K to create new chat
  useEffect(() => {
    const onShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        startChat();
      }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [authReady, createChat.isPending]);

  function startChat(prompt?: string) {
    if (!authReady || createChat.isPending || createChatInFlight.current) return;
    createChatInFlight.current = true;
    setActionError("");
    createChat.mutate(prompt);
  }

  function handleSaveRename(id: string) {
    const name = renameTitle.trim();
    if (!name || renameChat.isPending) return;
    renameChat.mutate({ id, name });
  }

  function selectChat(id: string) {
    setActive(id);
    setInitialPrompt("");
    if (window.matchMedia("(max-width: 767px)").matches) setSidebarOpen(false);
  }

  const activeChat = chats.data?.find((c) => c.id === active);

  return (
    <div className="bg-background-canvas font-body-md text-body-md text-on-surface antialiased min-h-screen selection:bg-accent-chroma selection:text-primary relative overflow-hidden flex">
      {/* Background Orbs */}
      <div className="pointer-events-none fixed top-0 right-1/4 -z-10 h-96 w-96 rounded-full bg-accent-chroma/15 blur-[128px]"></div>
      <div className="pointer-events-none fixed bottom-1/3 left-10 -z-10 h-80 w-80 rounded-full bg-secondary-container/20 blur-[140px]"></div>

      {/* LEFT SIDEBAR */}
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close conversation sidebar"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
        />
      )}
      <aside
        aria-label="Conversation sidebar"
        className={`fixed left-0 top-0 h-dvh ${sidebarOpen ? "w-72 max-w-[calc(100vw-2rem)] translate-x-0" : "w-16 -translate-x-full md:translate-x-0"} bg-surface-container-lowest/95 backdrop-blur-2xl z-50 flex flex-col justify-between p-space-md border-r border-glass-border shadow-[0_1px_8px_rgba(0,0,0,0.4)] transition-all duration-300`}
      >
        <div className="flex flex-col gap-space-md min-h-0">
          {/* Logo & Close toggle */}
          <div className={`flex ${sidebarOpen ? "items-center justify-between" : "flex-col items-center gap-3"} px-space-xs py-space-xs shrink-0`}>
            <Link href="/" className="flex items-center gap-space-sm group">
              <div className="w-8 h-8 rounded-lg bg-surface-secondary border border-glass-border flex items-center justify-center text-primary shadow-[0_0_16px_rgba(109,113,138,0.25)] group-hover:scale-105 transition-transform">
                <span className="material-symbols-outlined text-[18px]">biotech</span>
              </div>
              {sidebarOpen && <div className="flex flex-col">
                <span className="font-headline-sm text-[14px] leading-tight tracking-wider font-semibold text-primary">
                  MEDASSIST AI
                </span>
                <span className="font-caption text-caption text-outline uppercase tracking-widest">
                  Clinical Intelligence
                </span>
              </div>}
            </Link>
            <button
              aria-label={sidebarOpen ? "Collapse conversation sidebar" : "Expand conversation sidebar"}
              aria-expanded={sidebarOpen}
              onClick={() => setSidebarOpen((open) => !open)}
              type="button"
              className="w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">{sidebarOpen ? "dock_to_left" : "dock_to_right"}</span>
            </button>
          </div>

          {/* New Conversation Button & Search */}
          {sidebarOpen && <div className="flex flex-col gap-space-xs pt-space-xs shrink-0">
            <button
              onClick={() => startChat()}
              disabled={!authReady || createChat.isPending}
              className="w-full flex items-center justify-center gap-space-xs px-space-md py-space-sm rounded-xl bg-primary text-background-canvas font-medium text-[13px] hover:bg-white hover:shadow-[0_0_20px_rgba(206,204,220,0.3)] transition-all disabled:opacity-50"
              type="button"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              <span>{createChat.isPending ? "Initializing..." : "New Conversation"}</span>
              <span className="ml-auto text-[10px] font-label-code opacity-60">Ctrl K</span>
            </button>

            <div className="relative w-full mt-space-xs">
              <span className="material-symbols-outlined absolute left-3 top-2.5 text-[16px] text-outline">search</span>
              <input
                className="w-full pl-9 pr-space-md py-space-xs rounded-xl bg-surface-container-low border border-glass-border text-on-surface placeholder:text-outline text-[12px] font-body-sm focus:outline-none focus:ring-1 focus:ring-accent-chroma transition-all"
                placeholder="Search clinical consults..."
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>}

          {/* Active Protocol Feeds / Chat List */}
          {sidebarOpen && <div className="pt-space-sm flex-1 min-h-0 flex flex-col">
            <span className="px-space-xs font-caption text-caption text-outline uppercase tracking-wider block mb-space-xs shrink-0">
              Active Protocol Feeds
            </span>
            <nav className="soft-scroll flex flex-col gap-space-xs overflow-y-auto flex-1 pr-1">
              {!isLoaded || chats.isLoading ? (
                <div className="p-3 text-xs text-outline flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
                  Loading consults...
                </div>
              ) : chats.error ? (
                <div className="p-3 text-xs text-error">
                  Could not load consult history.{" "}
                  <button onClick={() => void chats.refetch()} className="underline ml-1">
                    Retry
                  </button>
                </div>
              ) : filteredChats.length > 0 ? (
                filteredChats.map((chat) => {
                  const isSelected = active === chat.id;
                  const isRenamingThis = renaming === chat.id;

                  return (
                    <div key={chat.id} className="relative group">
                      {isRenamingThis ? (
                        <div className="flex items-center gap-1 p-1 bg-surface-container-high rounded-lg">
                          <input
                            autoFocus
                            value={renameTitle}
                            onChange={(e) => setRenameTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.preventDefault();
                                handleSaveRename(chat.id);
                              }
                              if (e.key === "Escape") setRenaming(null);
                            }}
                            className="min-w-0 flex-1 rounded bg-surface-container-lowest px-2 py-1 text-xs text-primary focus:outline-none"
                          />
                          <button
                            onClick={() => handleSaveRename(chat.id)}
                            className="p-1 text-primary hover:text-white"
                          >
                            <span className="material-symbols-outlined text-[14px]">check</span>
                          </button>
                          <button onClick={() => setRenaming(null)} className="p-1 text-outline hover:text-primary">
                            <span className="material-symbols-outlined text-[14px]">close</span>
                          </button>
                        </div>
                      ) : (
                        <div
                          onClick={() => selectChat(chat.id)}
                          className={`group flex items-center justify-between px-space-sm py-space-xs rounded-lg transition-all cursor-pointer ${
                            isSelected
                              ? "bg-surface-container-high text-primary font-medium shadow-[0_0_12px_rgba(109,113,138,0.12)] border border-glass-border"
                              : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                          }`}
                        >
                          <div className="flex items-center gap-space-xs min-w-0">
                            <span
                              className={`material-symbols-outlined text-[16px] shrink-0 ${
                                isSelected ? "text-accent-chroma" : "text-outline"
                              }`}
                            >
                              biotech
                            </span>
                            <span className="truncate text-[13px] font-body-sm">{chat.title}</span>
                          </div>

                          <div className="relative">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setChatMenuOpen(chatMenuOpen === chat.id ? null : chat.id);
                              }}
                              aria-label={`Actions for ${chat.title}`}
                              type="button"
                              className="material-symbols-outlined text-[16px] opacity-0 group-hover:opacity-100 text-outline hover:text-primary shrink-0 transition-opacity p-0.5"
                            >
                              more_horiz
                            </button>

                            {/* Dropdown Menu */}
                            {chatMenuOpen === chat.id && (
                              <div
                                onClick={(e) => e.stopPropagation()}
                                className="absolute right-0 top-6 w-32 rounded-xl bg-surface-container-highest border border-glass-border p-1 shadow-2xl z-50 flex flex-col gap-0.5"
                              >
                                <button
                                  onClick={() => {
                                    setRenaming(chat.id);
                                    setRenameTitle(chat.title);
                                    setChatMenuOpen(null);
                                  }}
                                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-xs text-primary hover:bg-surface-container"
                                >
                                  <span className="material-symbols-outlined text-[14px]">edit</span>
                                  Rename
                                </button>
                                <button
                                  onClick={() => {
                                    if (window.confirm("Delete this conversation and its indexed reports?")) {
                                      deleteChat.mutate(chat.id);
                                    }
                                  }}
                                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-xs text-error hover:bg-error-container/30"
                                >
                                  <span className="material-symbols-outlined text-[14px]">delete</span>
                                  Delete
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="p-4 text-center text-xs text-outline">
                  {query ? "No matching consults" : "No active consults"}
                </div>
              )}
            </nav>
          </div>}
        </div>

        {/* User Card Bottom Section */}
        {sidebarOpen ? <div className="flex flex-col gap-space-xs pt-space-md border-t border-glass-border shrink-0">
          <div className="flex items-center gap-space-xs px-space-sm py-space-xs rounded-lg bg-surface-container-low/70 border border-glass-border">
            <span className="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_rgba(193,197,225,0.6)] animate-pulse"></span>
            <span className="font-caption text-[11px] text-text-highlight">Conversation workspace</span>
          </div>

          <div className="flex items-center justify-between px-space-sm py-space-xs rounded-xl bg-surface-container-low border border-glass-border">
            <div className="flex items-center gap-space-sm min-w-0">
              <div className="flex flex-col min-w-0">
                <span className="text-[13px] font-medium text-primary leading-tight truncate">
                  {user?.fullName || "Clinician / Patient"}
                </span>
                <span className="font-caption text-caption text-outline truncate">
                  {user?.primaryEmailAddress?.emailAddress || "Signed-in account"}
                </span>
              </div>
            </div>
            <div className="shrink-0 flex items-center">
              <UserButton afterSignOutUrl="/" />
            </div>
          </div>
        </div> : <div className="flex justify-center border-t border-glass-border pt-space-sm"><UserButton afterSignOutUrl="/" /></div>}
      </aside>

      {/* MAIN VIEWPORT */}
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${sidebarOpen ? "md:pl-72" : "md:pl-16"}`}>

        {/* Global Error Alert */}
        {actionError && (
          <div className="mx-8 mt-4 p-3 rounded-xl bg-error-container/40 border border-error text-error text-xs flex items-center justify-between">
            <span>{actionError}</span>
            <button onClick={() => setActionError("")} className="material-symbols-outlined text-[16px]">
              close
            </button>
          </div>
        )}

        {/* Active Consultation Panel */}
        {active ? (
          <AIChatPanel
            key={active}
            sessionId={active}
            title={activeChat?.title || "Clinical Consultation"}
            initialPrompt={initialPrompt}
            sidebarOpen={sidebarOpen}
            onDelete={() => deleteChat.mutate(active)}
            getToken={getToken}
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-xl mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-surface-container-high border border-glass-border flex items-center justify-center text-primary shadow-2xl mb-6">
              <span className="material-symbols-outlined text-[32px] text-accent-chroma">biotech</span>
            </div>
            <h2 className="font-headline-lg text-headline-md text-primary font-light mb-3">
              Precision Clinical Enclave
            </h2>
            <p className="font-body-md text-on-surface-variant leading-relaxed mb-6">
              Select an existing conversation or start a new one to ask questions about your health reports.
            </p>
            <button
              onClick={() => startChat()}
              disabled={!authReady || createChat.isPending}
              className="px-6 py-3 rounded-full bg-primary text-background-canvas font-medium text-sm hover:bg-white hover:shadow-[0_0_24px_rgba(206,204,220,0.35)] transition-all disabled:opacity-50"
            >
              {createChat.isPending ? <span className="inline-flex items-center gap-2" role="status"><span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" />Opening consultation…</span> : "Start New Consultation"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
