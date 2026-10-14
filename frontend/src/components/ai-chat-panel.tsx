"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ArrowUp, BookOpenText, Building2, ChevronDown, Download, FileText, Languages, LoaderCircle, Mail, MapPin, Mic, MicOff, MoreHorizontal, Paperclip, Send, Share2, ShieldCheck, Sparkles, Stethoscope, Trash2, Volume2, X } from "lucide-react";
import { api } from "@/lib/api";
import { MAX_REPORT_SIZE, uploadReport, type Report } from "@/lib/report-upload";
import { ReportsPanel } from "@/components/reports-panel";

type Citation = { report_id: string; report_name: string; section: string; page: number | null; excerpt: string };
type ChatMessage = { id: string; role: "user" | "assistant"; content: string; citations?: Citation[] | null; created_at: string };
type LiveTurn = { question: string; answer: string; citations: Citation[] };
type LanguageMode = "auto" | "english" | "kannada" | "bilingual";
type Recommendation = { title: string; detail: string; category: string };
type RecommendationResult = { recommendations?: Recommendation[]; specialists?: Recommendation[]; sources: Citation[]; disclaimer: string };
type HospitalResult = { id: string; name: string; city: string; specialization: string; address: string; phone: string | null; website: string | null; rating: number | null; reason: string };
type HospitalResponse = { hospitals: HospitalResult[]; specialties: string[]; disclaimer: string };
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const MAX_RECORDING_SECONDS = Number(process.env.NEXT_PUBLIC_VOICE_MAX_DURATION_SECONDS) || 180;

export function AIChatPanel({ sessionId, title, initialPrompt, onDelete, getToken }: { sessionId: string; title: string; initialPrompt: string; onDelete: () => void; getToken: () => Promise<string | null> }) {
  const queryClient = useQueryClient(); const fileInput = useRef<HTMLInputElement>(null); const [draft, setDraft] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [liveTurn, setLiveTurn] = useState<LiveTurn | null>(null); const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null); const [recommendationBusy, setRecommendationBusy] = useState(false);
  const [uploading, setUploading] = useState<{ name: string; percent: number } | null>(null); const [retryFile, setRetryFile] = useState<File | null>(null); const [uploadError, setUploadError] = useState("");
  const [recording, setRecording] = useState(false); const [transcribing, setTranscribing] = useState(false); const [recordingSeconds, setRecordingSeconds] = useState(0); const [transcriptionSeconds, setTranscriptionSeconds] = useState(0); const [voiceDone, setVoiceDone] = useState(false); const [hospitalInput, setHospitalInput] = useState({ city: "", region: "", location: "", condition: "" }); const [hospitalResults, setHospitalResults] = useState<HospitalResponse | null>(null); const [hospitalBusy, setHospitalBusy] = useState(false); const [emailOpen, setEmailOpen] = useState(false); const [emailAddress, setEmailAddress] = useState(""); const [includeSummaries, setIncludeSummaries] = useState(true); const [emailBusy, setEmailBusy] = useState(false); const recorderRef = useRef<MediaRecorder | null>(null); const streamRef = useRef<MediaStream | null>(null); const chunksRef = useRef<Blob[]>([]);
  const messages = useQuery({ queryKey: ["messages", sessionId], queryFn: async () => api<ChatMessage[]>(`/chats/${sessionId}/messages`, (await getToken()) ?? "") });
  const memoryQuery = useQuery({ queryKey: ["session-memory", sessionId], queryFn: async () => api<{ language_mode: LanguageMode }>(`/memory/session/${sessionId}`, (await getToken()) ?? "") });
  const reports = useQuery({ queryKey: ["reports", sessionId], queryFn: async () => api<Report[]>(`/reports?session_id=${encodeURIComponent(sessionId)}`, (await getToken()) ?? ""), refetchInterval: query => query.state.data?.some(isProcessing) ? 2_000 : false });
  const languageMode = memoryQuery.data?.language_mode ?? "auto";
  const hasReports = Boolean(reports.data?.length);
  const reportsReady = !reports.isLoading && !reports.data?.some(report => report.processing_status === "pending" || report.processing_status === "processing");
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    if (!reports.data?.some(report => report.processing_status === "pending" || report.processing_status === "processing")) return;
    const timer = window.setInterval(() => setClock(Date.now()), 2_000);
    return () => window.clearInterval(timer);
  }, [reports.data]);
  const timedOutReport = reports.data?.find(report => isProcessing(report) && clock - new Date(report.upload_date).getTime() >= 5 * 60_000);
  useEffect(() => { if (initialPrompt) setDraft(initialPrompt); }, [initialPrompt]);
  async function handleFiles(files: FileList | File[]) {
    setUploadError(""); setRetryFile(null);
    for (const file of Array.from(files)) {
      const extension = file.name.split(".").pop()?.toLowerCase();
      if (!extension || !["pdf", "png", "jpg", "jpeg", "webp"].includes(extension)) { setUploadError(`${file.name}: choose a PDF, PNG, JPG, JPEG, or WEBP file.`); continue; }
      if (file.size === 0 || file.size > MAX_REPORT_SIZE) { setUploadError(`${file.name}: choose a non-empty file up to 20 MB.`); setRetryFile(file); continue; }
      try {
        const token = await getToken(); if (!token) throw new Error("Your session expired. Please sign in again.");
        setUploading({ name: file.name, percent: 0 });
        const uploaded = await uploadReport(file, sessionId, token, percent => setUploading({ name: file.name, percent }));
        queryClient.setQueryData<Report[]>(["reports", sessionId], current => [uploaded, ...(current ?? []).filter(report => report.id !== uploaded.id)]);
        await queryClient.invalidateQueries({ queryKey: ["reports", sessionId] });
      } catch (reason) { setUploadError(reason instanceof Error ? reason.message : "Could not upload this report."); setRetryFile(file); }
      finally { setUploading(null); }
    }
  }
  useEffect(() => () => { const recorder = recorderRef.current; if (recorder && recorder.state !== "inactive") { recorder.onstop = null; recorder.stop(); } streamRef.current?.getTracks().forEach(track => track.stop()); if (typeof window !== "undefined") window.speechSynthesis?.cancel(); }, []);
  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => setRecordingSeconds(seconds => {
      const next = seconds + 1;
      if (seconds < MAX_RECORDING_SECONDS && next >= MAX_RECORDING_SECONDS) window.setTimeout(() => stopRecording(), 0);
      return Math.min(next, MAX_RECORDING_SECONDS);
    }), 1_000);
    return () => window.clearInterval(timer);
  }, [recording]);
  useEffect(() => {
    if (!transcribing) return;
    setTranscriptionSeconds(0);
    const timer = window.setInterval(() => setTranscriptionSeconds(seconds => seconds + 1), 1_000);
    return () => window.clearInterval(timer);
  }, [transcribing]);
  useEffect(() => {
    if (!emailOpen) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => { if (event.key === "Escape" && !emailBusy) setEmailOpen(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [emailOpen, emailBusy]);

  async function setLanguage(mode: LanguageMode) {
    try { await api(`/ai/language-mode`, (await getToken()) ?? "", { method: "POST", body: JSON.stringify({ session_id: sessionId, mode }) }); await queryClient.invalidateQueries({ queryKey: ["session-memory", sessionId] }); }
    catch { setError("Could not save the language preference. Please try again."); }
  }

  async function requestRecommendation(kind: "medical" | "doctor") {
    setRecommendationBusy(true); setRecommendation(null); setError("");
    try {
      const result = await api<RecommendationResult>(`/ai/${kind === "medical" ? "recommendations" : "doctor-recommendation"}`, (await getToken()) ?? "", { method: "POST", body: JSON.stringify({ session_id: sessionId, question: kind === "medical" ? "Give cautious, general recommendations based on my reports, including food, precautions, and symptoms to monitor." : "Based on the diagnoses, conditions, or symptoms in my reports, which specialist category should I consider?" }) });
      setRecommendation(result); await queryClient.invalidateQueries({ queryKey: ["session-memory", sessionId] });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load recommendations."); }
    finally { setRecommendationBusy(false); }
  }

  async function finishVoice(blob: Blob) {
    setTranscribing(true); setVoiceDone(false); setError("");
    try {
      const token = await getToken(); if (!token) throw new Error("Your session expired. Please sign in again.");
      const extension = blob.type.includes("mp4") ? "mp4" : "webm";
      const form = new FormData(); form.append("session_id", sessionId); form.append("file", new File([blob], `voice-input.${extension}`, { type: blob.type || "audio/webm" }));
      const response = await fetch(`${API_BASE}/ai/voice`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form, cache: "no-store" });
      if (!response.ok) { let detail = "Could not transcribe the recording."; try { detail = (await response.json()).detail ?? detail; } catch { /* use default */ } throw new Error(detail); }
      const result = await response.json() as { text: string; language?: string };
      setTranscribing(false); setDraft(result.text); if (await ask(result.text)) { setVoiceDone(true); window.setTimeout(() => setVoiceDone(false), 3_000); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not transcribe the recording."); }
    finally { setTranscribing(false); }
  }

  async function startRecording() {
    setError("");
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw new Error("Voice recording is not supported in this browser.");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } });
      streamRef.current = stream; chunksRef.current = [];
      const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find(type => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined); recorderRef.current = recorder;
      recorder.ondataavailable = event => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onerror = () => { recorder.onstop = null; stream.getTracks().forEach(track => track.stop()); streamRef.current = null; setRecording(false); setError("The microphone recording was interrupted. Please try again."); };
      recorder.onstop = () => { const blob = new Blob(chunksRef.current, { type: recorder.mimeType }); stream.getTracks().forEach(track => track.stop()); streamRef.current = null; if (blob.size) void finishVoice(blob); };
      setRecordingSeconds(0); setVoiceDone(false); recorder.start(); setRecording(true);
    } catch (reason) { streamRef.current?.getTracks().forEach(track => track.stop()); streamRef.current = null; setRecording(false); setError(reason instanceof Error ? reason.message : "Microphone access was unavailable."); }
  }

  function stopRecording() { recorderRef.current?.stop(); setRecording(false); }

  async function findHospitals(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setHospitalBusy(true); setHospitalResults(null); setError("");
    try { const result = await api<HospitalResponse>("/ai/hospital-recommendation", (await getToken()) ?? "", { method: "POST", body: JSON.stringify({ session_id: sessionId, ...hospitalInput }) }); setHospitalResults(result); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Hospital search failed."); }
    finally { setHospitalBusy(false); }
  }

  async function downloadExport(format: "pdf" | "txt") {
    try {
      const token = await getToken(); if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/export/${format}/${sessionId}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
      if (!response.ok) throw new Error("The chat export could not be created.");
      const blob = await response.blob(); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `medassist-chat.${format}`; anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The chat export failed."); }
  }

  async function sendEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setEmailBusy(true); setError("");
    try { await api("/share/email", (await getToken()) ?? "", { method: "POST", body: JSON.stringify({ session_id: sessionId, recipient_email: emailAddress, include_report_summaries: includeSummaries }) }); setEmailOpen(false); setEmailAddress(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The email could not be sent."); }
    finally { setEmailBusy(false); }
  }

  async function ask(rawQuestion: string): Promise<boolean> {
    const question = rawQuestion.trim(); if (!question || busy) return false;
    if (!reportsReady || uploading) { setError("Wait for report processing to finish before asking about an attached report."); return false; }
    setDraft(""); setError(""); setBusy(true); setLiveTurn({ question, answer: "", citations: [] });
    try {
      const token = await getToken(); if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/ai/chat`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", Accept: "text/event-stream" }, body: JSON.stringify({ session_id: sessionId, question }), cache: "no-store" });
      if (!response.ok || !response.body) {
        let message = "Could not start the response.";
        try { const body = await response.json(); message = body.detail ?? message; } catch { /* keep the safe default */ }
        throw new Error(message);
      }
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let streamError = "";
      const consume = (frame: string) => {
        const data = frame.split("\n").filter(line => line.startsWith("data:")).map(line => line.slice(5).trim()).join("\n");
        if (!data) return;
        const event = JSON.parse(data) as { type: string; content?: string; citations?: Citation[]; message?: string };
        if (event.type === "citations") setLiveTurn(current => current ? { ...current, citations: event.citations ?? [] } : current);
        if (event.type === "token" && event.content) setLiveTurn(current => current ? { ...current, answer: current.answer + event.content } : current);
        if (event.type === "error") streamError = event.message ?? "Could not complete the answer.";
      };
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const frames = buffer.split("\n\n"); buffer = frames.pop() ?? "";
        for (const frame of frames) consume(frame);
        if (done) break;
      }
      if (buffer.trim()) consume(buffer);
      if (streamError) throw new Error(streamError);
      await queryClient.invalidateQueries({ queryKey: ["messages", sessionId] });
      setLiveTurn(null);
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not complete the answer.");
      await queryClient.invalidateQueries({ queryKey: ["messages", sessionId] });
      setLiveTurn(null);
      return false;
    } finally { setBusy(false); }
  }

  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void ask(draft); }
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void ask(draft); } }
  const hasMessages = Boolean(messages.data?.length || liveTurn);

  return <div className="flex h-full min-h-0 flex-1 flex-col" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (event.dataTransfer.files?.length) void handleFiles(event.dataTransfer.files); }}>
    <div className="mb-3 flex items-center justify-between gap-3 border-b border-slate-200 pb-3"><div className="min-w-0"><div className="text-[10px] font-medium uppercase tracking-[.14em] text-slate-400">Conversation</div><h1 className="truncate text-base font-semibold text-slate-800">{title}</h1></div><div className="flex shrink-0 items-center gap-1"><button type="button" onClick={() => setEmailOpen(true)} aria-label="Share conversation by email" className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-600 hover:bg-blue-50 hover:text-blue-700"><Share2 size={15}/><span className="hidden sm:inline">Share</span></button><details className="relative"><summary aria-label="More conversation actions" className="flex cursor-pointer list-none items-center gap-1 rounded-lg px-2.5 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"><MoreHorizontal size={17}/><ChevronDown size={12}/></summary><div className="absolute right-0 z-30 mt-1 w-48 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl"><button type="button" onClick={() => void downloadExport("pdf")} className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-slate-700 hover:bg-slate-50"><Download size={14}/>Export PDF</button><button type="button" onClick={() => void downloadExport("txt")} className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-slate-700 hover:bg-slate-50"><FileText size={14}/>Export TXT</button><button type="button" onClick={() => { if (window.confirm("Delete this conversation and its attached reports?")) onDelete(); }} className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-rose-600 hover:bg-rose-50"><Trash2 size={14}/>Delete conversation</button></div></details></div></div>
    <details className="mb-3 rounded-xl border border-slate-200 bg-white"><summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2.5 text-xs font-medium text-slate-600"><span className="flex items-center gap-2"><Sparkles size={14} className="text-blue-600"/>Health tools and language</span><span className="text-[10px] text-slate-400">{languageMode === "auto" ? "Auto" : languageMode === "bilingual" ? "English + ಕನ್ನಡ" : languageMode === "kannada" ? "ಕನ್ನಡ" : "English"}</span></summary><div className="border-t border-slate-100 p-3">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2.5"><label className="flex items-center gap-2 text-xs font-medium text-slate-600"><Languages size={15} className="text-blue-600"/>Response language</label><select aria-label="Response language" value={languageMode} onChange={event => void setLanguage(event.target.value as LanguageMode)} className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 outline-none focus:ring-2 focus:ring-blue-200"><option value="auto">Auto-detect</option><option value="english">English</option><option value="kannada">Kannada</option><option value="bilingual">English + Kannada</option></select></div>
    <div className="mb-4 flex flex-wrap gap-2"><button type="button" onClick={() => void requestRecommendation("medical")} disabled={recommendationBusy} className="inline-flex items-center gap-1.5 rounded-lg border border-blue-100 bg-white px-3 py-2 text-xs font-medium text-blue-700 transition hover:bg-blue-50 disabled:opacity-60"><Sparkles size={14}/>Report-based recommendations</button><button type="button" onClick={() => void requestRecommendation("doctor")} disabled={recommendationBusy} className="inline-flex items-center gap-1.5 rounded-lg border border-blue-100 bg-white px-3 py-2 text-xs font-medium text-blue-700 transition hover:bg-blue-50 disabled:opacity-60"><Stethoscope size={14}/>Specialist suggestions</button>{recommendationBusy && <span className="inline-flex items-center gap-1.5 px-2 text-xs text-slate-400"><LoaderCircle size={14} className="animate-spin"/>Preparing…</span>}</div>
    {recommendation && <section aria-live="polite" className="mb-5 rounded-2xl border border-emerald-100 bg-emerald-50/40 p-4"><h3 className="mb-3 text-sm font-semibold text-slate-800">{recommendation.specialists ? "Specialist categories to discuss" : "Suggestions based on this chat’s reports"}</h3><div className="grid gap-2 sm:grid-cols-2">{(recommendation.specialists ?? recommendation.recommendations ?? []).map((item, index) => <article key={`${item.title}-${index}`} className="rounded-xl border border-white bg-white p-3"><div className="text-xs font-semibold text-slate-800">{item.title}</div><p className="mt-1.5 text-xs leading-5 text-slate-600">{item.detail}</p></article>)}</div>{recommendation.sources.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{recommendation.sources.map((source, index) => <span key={`${source.report_id}-${index}`} className="rounded-full border border-blue-100 bg-white px-2.5 py-1 text-[10px] text-blue-700">{source.report_name} · {source.section}</span>)}</div>}<p className="mt-3 text-[10px] leading-4 text-slate-500">{recommendation.disclaimer}</p></section>}
    <details className="mb-4 rounded-xl border border-slate-100"><summary className="flex cursor-pointer items-center gap-2 px-3 py-2.5 text-xs font-medium text-slate-600"><Building2 size={15} className="text-blue-600"/>Find hospitals by location</summary><div className="p-3"><p className="mb-3 text-xs leading-5 text-slate-500">Enter a city and nearby area. Your location is never detected automatically.</p><form onSubmit={findHospitals} className="grid gap-2 sm:grid-cols-2"><input required minLength={2} maxLength={120} aria-label="City" placeholder="City (e.g. Mysore)" value={hospitalInput.city} onChange={event => setHospitalInput({ ...hospitalInput, city: event.target.value })} className="h-10 rounded-lg border border-slate-200 px-3 text-xs outline-none focus:border-blue-300"/><input required minLength={2} maxLength={120} aria-label="Region" placeholder="Region / district" value={hospitalInput.region} onChange={event => setHospitalInput({ ...hospitalInput, region: event.target.value })} className="h-10 rounded-lg border border-slate-200 px-3 text-xs outline-none focus:border-blue-300"/><input required minLength={2} maxLength={240} aria-label="Location" placeholder="Local area / location" value={hospitalInput.location} onChange={event => setHospitalInput({ ...hospitalInput, location: event.target.value })} className="h-10 rounded-lg border border-slate-200 px-3 text-xs outline-none focus:border-blue-300"/><input maxLength={500} aria-label="Condition" placeholder="Condition or diagnosis (optional)" value={hospitalInput.condition} onChange={event => setHospitalInput({ ...hospitalInput, condition: event.target.value })} className="h-10 rounded-lg border border-slate-200 px-3 text-xs outline-none focus:border-blue-300"/><button disabled={hospitalBusy} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60 sm:col-span-2"><MapPin size={14}/>{hospitalBusy ? "Searching directory…" : "Find hospitals"}</button></form>
      {hospitalResults && <div aria-live="polite" className="mt-4 space-y-2">{hospitalResults.specialties.length > 0 && <p className="text-[11px] text-slate-500">Matching specialties: {hospitalResults.specialties.join(", ")}</p>}{hospitalResults.hospitals.length ? hospitalResults.hospitals.map(item => <article key={item.id} className="rounded-xl border border-blue-100 bg-blue-50/40 p-3"><div className="flex flex-wrap items-start justify-between gap-2"><div><h4 className="text-xs font-semibold text-slate-800">{item.name}</h4><p className="mt-1 text-[11px] text-blue-700">{item.specialization} · {item.city}{item.rating !== null ? ` · ${item.rating.toFixed(1)}★` : ""}</p></div>{item.phone && <a className="text-xs text-blue-700 underline" href={`tel:${item.phone}`}>{item.phone}</a>}</div><p className="mt-2 text-xs text-slate-600">{item.address}</p>{item.website?.startsWith("https://") && <a href={item.website} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-blue-700 underline">Hospital website</a>}<p className="mt-2 text-[10px] text-slate-500">{item.reason}</p></article>) : <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-500">No matching hospitals found in the imported directory for this location.</p>}<p className="text-[10px] leading-4 text-slate-500">{hospitalResults.disclaimer}</p></div>}
    </div></details>
    </div></details>
    <ReportsPanel sessionId={sessionId} getToken={getToken}/>
    <div className="soft-scroll min-h-0 flex-1 space-y-5 overflow-y-auto py-3">
      {messages.isLoading && <div role="status" aria-label="Loading chat history" className="space-y-4 py-4"><span className="sr-only">Loading this chat…</span><div className="ml-auto h-20 w-3/4 animate-pulse rounded-2xl bg-blue-50"/><div className="h-28 w-5/6 animate-pulse rounded-2xl bg-slate-100"/><div className="ml-auto h-16 w-2/3 animate-pulse rounded-2xl bg-blue-50"/></div>}
      {messages.isError && <div role="alert" className="rounded-xl border border-rose-100 bg-rose-50 p-3 text-xs text-rose-700">Could not load messages for this conversation. <button type="button" onClick={() => void messages.refetch()} className="font-semibold underline">Retry</button></div>}
      {!hasMessages && !messages.isLoading && !messages.isError && <div className="flex min-h-[34vh] flex-col items-center justify-center px-4 py-10 text-center"><div className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-blue-50 text-blue-600"><Sparkles size={21}/></div><h2 className="text-2xl font-semibold tracking-tight text-slate-800 sm:text-3xl">How can I help with your health today?</h2><p className="mt-3 max-w-lg text-sm leading-6 text-slate-500">Ask a general health question, or attach a report for answers grounded in your document.</p><div className="mt-6 flex max-w-2xl flex-wrap justify-center gap-2">{["Summarize a medical report", "Explain a diagnosis", "Find a specialist", "Understand lab results"].map(question => <button key={question} type="button" onClick={() => setDraft(question)} className="rounded-full border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700">{question}</button>)}</div></div>}
      {messages.data?.map(message => <MessageBubble key={message.id} role={message.role} content={message.content} citations={message.citations ?? []}/>)}
      {liveTurn && <><MessageBubble role="user" content={liveTurn.question} citations={[]}/><MessageBubble role="assistant" content={liveTurn.answer} citations={liveTurn.citations} streaming={busy}/></>}
    </div>
    {error && <div role="alert" className="mb-3 flex items-start gap-2 rounded-xl border border-rose-100 bg-rose-50 px-3.5 py-3 text-xs text-rose-700"><AlertCircle size={15} className="mt-0.5 shrink-0"/><span>{error}</span></div>}
    {(recording || transcribing || busy) && <div role="status" aria-live="polite" className={`mb-2 flex w-fit items-center gap-2 rounded-full border px-3 py-2 text-xs shadow-sm ${recording ? "border-rose-200 bg-rose-50 text-rose-700" : "border-blue-100 bg-blue-50 text-blue-700"}`}>{recording ? <><span className="h-2 w-2 animate-ping rounded-full bg-rose-500"/>Recording · {formatClock(recordingSeconds)}</> : transcribing ? <><LoaderCircle size={14} className="animate-spin"/>Transcribing voice…</> : <>🤖 Thinking…</>}</div>}
    <form onSubmit={submit} className="mt-2 shrink-0 rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_8px_32px_rgba(38,67,112,0.08)]"><input ref={fileInput} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" multiple className="sr-only" onChange={event => { if (event.target.files?.length) void handleFiles(event.target.files); event.currentTarget.value = ""; }}/>{hasReports && <div className="mb-2 flex flex-wrap gap-1.5 px-1">{reports.data?.map(report => <span key={report.id} className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-blue-100 bg-blue-50/60 px-2.5 py-1.5 text-[11px] text-slate-600"><FileText size={12} className="shrink-0 text-blue-600"/><span className="max-w-40 truncate">{report.file_name}</span><span className={`whitespace-nowrap text-[10px] ${report.processing_status === "completed" ? "text-emerald-700" : report.processing_status === "failed" ? "text-rose-600" : "text-blue-700"}`}>{reportStatus(report, clock)}</span><button type="button" title={`Remove ${report.file_name} from this chat`} aria-label={`Remove ${report.file_name}`} onClick={async () => { try { await api<void>(`/reports/${report.id}`, (await getToken()) ?? "", { method: "DELETE" }); await queryClient.invalidateQueries({ queryKey: ["reports", sessionId] }); } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not remove this report."); } }} className="rounded p-0.5 text-slate-400 hover:bg-white hover:text-rose-600"><X size={12}/></button></span>)}</div>}{timedOutReport && <div role="status" className="mb-2 flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800"><span>Report processing is taking longer than expected. Status will continue updating; retry the report if processing fails.</span><button type="button" onClick={() => void reports.refetch()} className="ml-2 shrink-0 font-semibold underline">Check status</button></div>}{uploading && <div role="status" className="mb-2 rounded-lg border border-blue-100 bg-blue-50/60 px-3 py-2"><div className="mb-1 flex items-center justify-between gap-3 text-[11px]"><span className="flex min-w-0 items-center gap-1.5 text-blue-700"><LoaderCircle size={12} className="animate-spin"/><span className="truncate">{uploading.percent >= 100 ? `Saving ${uploading.name}` : `Uploading ${uploading.name}`}</span></span><span className="shrink-0 text-slate-500">{uploading.percent}%</span></div><div className="h-1 overflow-hidden rounded-full bg-blue-100"><div className="h-full bg-blue-600 transition-all" style={{ width: `${uploading.percent}%` }}/></div></div>}{uploadError && <div role="alert" className="mb-2 flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700"><AlertCircle size={14}/><span className="flex-1">{uploadError}</span>{retryFile && <button type="button" onClick={() => void handleFiles([retryFile])} className="font-semibold underline">Retry</button>}<button type="button" onClick={() => { setUploadError(""); setRetryFile(null); }} aria-label="Dismiss upload error"><X size={13}/></button></div>}<label htmlFor="medical-question" className="sr-only">Ask a question about your health</label><textarea id="medical-question" value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={onKeyDown} disabled={busy || recording || transcribing} rows={2} maxLength={8000} placeholder={hasReports ? "Ask anything about your health reports…" : "Ask anything about your health…"} className="max-h-36 min-h-14 w-full resize-y bg-transparent px-3 py-2 text-sm leading-6 outline-none placeholder:text-slate-400 disabled:opacity-60"/><div className="flex items-center justify-between px-2 pb-1"><div className="flex min-w-0 items-center gap-1.5"><button type="button" onClick={() => fileInput.current?.click()} disabled={Boolean(uploading)} aria-label="Attach medical report" title="Attach report" className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-slate-500 transition hover:bg-blue-50 hover:text-blue-700 disabled:opacity-50"><Paperclip size={17}/></button><button type="button" onClick={() => recording ? stopRecording() : void startRecording()} disabled={busy || transcribing} aria-label={recording ? "Stop voice recording" : "Start voice input"} className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl transition ${recording ? "animate-pulse bg-rose-100 text-rose-700" : "bg-slate-100 text-slate-600 hover:bg-blue-50 hover:text-blue-700"}`}>{recording ? <MicOff size={16}/> : <Mic size={16}/>}</button><span aria-live="polite" className={`truncate text-[10px] ${recording ? "font-medium text-rose-600" : "text-slate-400"}`}>{recording ? `🎙 Recording ${formatClock(recordingSeconds)} · click to stop` : transcribing ? `⏳ Transcribing voice · ${formatClock(transcriptionSeconds)}` : busy ? "🤖 Generating response…" : voiceDone ? "✓ Response ready" : uploading ? "Uploading report…" : hasReports ? "Report context is ready when processing completes" : "General health information · no report required"}</span></div><button type="submit" disabled={busy || recording || transcribing || !draft.trim() || !reportsReady || Boolean(uploading)} aria-label="Send question" className="grid h-9 w-9 place-items-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-200">{busy ? <LoaderCircle size={16} className="animate-spin"/> : <ArrowUp size={17}/>}</button></div></form>
    <p className="mt-2 px-1 text-center text-[10px] leading-4 text-slate-400">Health information is educational and is not a substitute for professional medical advice.</p>
    {emailOpen && <div role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !emailBusy) setEmailOpen(false); }} className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm"><form role="dialog" aria-modal="true" aria-labelledby="email-share-title" onSubmit={sendEmail} className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl"><div className="mb-4 flex items-center justify-between"><h3 id="email-share-title" className="text-base font-semibold text-slate-800">Share chat summary</h3><button type="button" disabled={emailBusy} onClick={() => setEmailOpen(false)} aria-label="Close email dialog" className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 disabled:opacity-50"><X size={17}/></button></div><p className="mb-4 text-xs leading-5 text-slate-500">Send this conversation, citations, and recommendations to an email address you choose.</p><label htmlFor="share-email" className="mb-1.5 block text-xs font-medium text-slate-600">Recipient email</label><input id="share-email" required type="email" value={emailAddress} onChange={event => setEmailAddress(event.target.value)} className="h-10 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-blue-300" placeholder="name@example.com"/><label className="mt-3 flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={includeSummaries} onChange={event => setIncludeSummaries(event.target.checked)} className="rounded border-slate-300 text-blue-600"/>Include saved report summaries</label><p className="mt-3 text-[10px] leading-4 text-amber-700">Medical information will be sent to the address entered. Check it before sharing.</p><div className="mt-5 flex justify-end gap-2"><button type="button" disabled={emailBusy} onClick={() => setEmailOpen(false)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600 disabled:opacity-50">Cancel</button><button disabled={emailBusy} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60"><Send size={13}/>{emailBusy ? "Sending…" : "Send summary"}</button></div></form></div>}
  </div>;
}

function MessageBubble({ role, content, citations, streaming = false }: { role: string; content: string; citations: Citation[]; streaming?: boolean }) {
  function listen() { if (typeof window === "undefined" || !window.speechSynthesis) return; window.speechSynthesis.cancel(); for (const part of content.split(/\n\n+/).filter(Boolean)) { const utterance = new SpeechSynthesisUtterance(part); utterance.lang = /[\u0C80-\u0CFF]/.test(part) ? "kn-IN" : "en-US"; utterance.rate = 0.95; window.speechSynthesis.speak(utterance); } }
  return <article className={`rounded-2xl border p-4 md:p-5 ${role === "user" ? "ml-6 border-blue-100 bg-blue-50/60 md:ml-16" : "mr-2 border-slate-200 bg-white md:mr-10"}`}><div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">{role === "assistant" ? <Sparkles size={13} className="text-blue-500"/> : null}{role === "assistant" ? "MedAssist AI" : "You"}{role === "assistant" && content && !streaming && <button type="button" onClick={listen} aria-label="Listen to this answer" className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 text-[10px] normal-case tracking-normal text-blue-700 hover:bg-blue-50"><Volume2 size={13}/>Listen</button>}</div><p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{content}{streaming && <span className="ml-1 inline-block h-4 w-1 animate-pulse rounded bg-blue-500 align-middle"/>}</p>{citations.length > 0 && <div className="mt-4 border-t border-slate-100 pt-3"><div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400"><BookOpenText size={13}/>Sources from your reports</div><div className="grid gap-2 sm:grid-cols-2">{citations.map((citation, index) => <div key={`${citation.report_id}-${citation.section}-${citation.page ?? 0}-${index}`} className="rounded-xl border border-blue-100/80 bg-blue-50/40 p-3"><div className="flex items-start gap-2"><FileText size={14} className="mt-0.5 shrink-0 text-blue-600"/><div className="min-w-0"><div className="truncate text-[11px] font-semibold text-slate-700">{citation.report_name}</div><div className="mt-0.5 text-[10px] font-medium text-blue-700">{citation.section}{citation.page ? ` · Page ${citation.page}` : ""}</div></div></div><p className="mt-2 line-clamp-3 text-[10px] leading-4 text-slate-500">{citation.excerpt}</p></div>)}</div></div>}</article>;
}

function formatClock(seconds: number) { return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`; }
function isProcessing(report: Report) { return report.processing_status === "pending" || report.processing_status === "processing"; }
function reportStatus(report: Report, now: number) {
  if (report.processing_status === "completed") return "✓ Ready";
  if (report.processing_status === "failed") return "Processing failed";
  const elapsedSeconds = Math.max(0, Math.floor((now - new Date(report.upload_date).getTime()) / 1_000));
  const eta = Math.max(3, Math.ceil(report.file_size / (1024 * 1024) * 8) - elapsedSeconds);
  const stage = report.processing_stage === "extracting_text" ? "Extracting text" : report.processing_stage === "generating_embeddings" ? "Generating embeddings" : "Queued";
  return `${stage} · ~${eta}s left`;
}
