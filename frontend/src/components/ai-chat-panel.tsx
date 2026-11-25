"use client";

import { FormEvent, KeyboardEvent as ReactKeyboardEvent, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MAX_REPORT_SIZE, uploadReport, type Report } from "@/lib/report-upload";
import { ReportsPanel } from "@/components/reports-panel";

export type Citation = { source_type?: "medical_knowledge"; report_id?: string; report_name?: string; title?: string; organization?: string; source_url?: string; section?: string; page?: number | null; version?: string; excerpt: string };
export type ChatMessage = { id: string; role: "user" | "assistant"; content: string; citations?: Citation[] | null; created_at: string };
type LiveTurn = { question: string; answer: string; citations: Citation[]; medicalCitations: Citation[] };
type LanguageMode = "auto" | "english" | "kannada" | "bilingual";
type HospitalLocation = { city: string; region?: string; location?: string; postal_code?: string };

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const MAX_RECORDING_SECONDS = Number(process.env.NEXT_PUBLIC_VOICE_MAX_DURATION_SECONDS) || 180;

export function AIChatPanel({
  sessionId,
  title,
  initialPrompt,
  sidebarOpen,
  onDelete,
  getToken,
}: {
  sessionId: string;
  title: string;
  initialPrompt: string;
  sidebarOpen: boolean;
  onDelete: () => void;
  getToken: () => Promise<string | null>;
}) {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const generationControllerRef = useRef<AbortController | null>(null);

  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [liveTurn, setLiveTurn] = useState<LiveTurn | null>(null);

  // Health tools state
  const [toolsOpen, setToolsOpen] = useState(false);
  const [hospitalLocationNeeded, setHospitalLocationNeeded] = useState(false);
  const [hospitalLocation, setHospitalLocation] = useState({ city: "", region: "", location: "", postal_code: "" });

  // Upload state
  const [uploading, setUploading] = useState<{ name: string; size: number; percent: number } | null>(null);
  const [retryFile, setRetryFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [attachmentMenuOpen, setAttachmentMenuOpen] = useState(false);
  const [reportsModalOpen, setReportsModalOpen] = useState(false);

  // Voice recording state
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [transcriptionSeconds, setTranscriptionSeconds] = useState(0);
  const [voiceDone, setVoiceDone] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Export & Share modal state
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [emailAddress, setEmailAddress] = useState("");
  const [includeSummaries, setIncludeSummaries] = useState(true);
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [exportFormat, setExportFormat] = useState<"pdf" | "txt">("pdf");

  useEffect(() => {
    if (!shareModalOpen && !reportsModalOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setShareModalOpen(false);
      setReportsModalOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [shareModalOpen, reportsModalOpen]);

  // Queries
  const messages = useQuery({
    queryKey: ["messages", sessionId],
    queryFn: async () => api<ChatMessage[]>(`/chats/${sessionId}/messages`, (await getToken()) ?? ""),
  });

  const memoryQuery = useQuery({
    queryKey: ["session-memory", sessionId],
    queryFn: async () => api<{ language_mode: LanguageMode; memory: Record<string, unknown> }>(`/memory/session/${sessionId}`, (await getToken()) ?? ""),
  });

  const reports = useQuery({
    queryKey: ["reports", sessionId],
    queryFn: async () => api<Report[]>(`/reports?session_id=${encodeURIComponent(sessionId)}`, (await getToken()) ?? ""),
    refetchInterval: (query) => (query.state.data?.some(isProcessing) ? 2_000 : false),
  });

  const languageMode = memoryQuery.data?.language_mode ?? "auto";
  const lastUserQuestion = [...(messages.data ?? [])].reverse().find((message) => message.role === "user")?.content ?? "";
  const hasReports = Boolean(reports.data?.length);
  const reportsReady = !reports.isLoading && !reports.isError && !reports.data?.some(isProcessing);
  const activeReport = reports.data?.[0];

  useEffect(() => {
    if (memoryQuery.data?.memory?.pending_action === "hospital_location") setHospitalLocationNeeded(true);
  }, [memoryQuery.data]);

  useEffect(() => {
    if (initialPrompt) setDraft(initialPrompt);
  }, [initialPrompt]);

  // Voice recording timers
  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => {
      setRecordingSeconds((sec) => {
        const next = sec + 1;
        if (sec < MAX_RECORDING_SECONDS && next >= MAX_RECORDING_SECONDS) {
          window.setTimeout(() => stopRecording(), 0);
        }
        return Math.min(next, MAX_RECORDING_SECONDS);
      });
    }, 1_000);
    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(() => {
    if (!transcribing) return;
    setTranscriptionSeconds(0);
    const timer = window.setInterval(() => setTranscriptionSeconds((sec) => sec + 1), 1_000);
    return () => window.clearInterval(timer);
  }, [transcribing]);

  // Cleanup audio tracks on unmount
  useEffect(() => {
    return () => {
      const rec = recorderRef.current;
      if (rec && rec.state !== "inactive") {
        rec.onstop = null;
        rec.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      if (typeof window !== "undefined") window.speechSynthesis?.cancel();
    };
  }, []);

  async function handleFiles(files: FileList | File[]) {
    setUploadError("");
    setRetryFile(null);
    setAttachmentMenuOpen(false);

    for (const file of Array.from(files)) {
      const extension = file.name.split(".").pop()?.toLowerCase();
      if (!extension || !["pdf", "png", "jpg", "jpeg", "webp"].includes(extension)) {
        setUploadError(`${file.name}: please choose a PDF, PNG, JPG, JPEG, or WEBP file.`);
        continue;
      }
      if (file.size === 0 || file.size > MAX_REPORT_SIZE) {
        setUploadError(`${file.name}: please choose a file up to 20 MB.`);
        setRetryFile(file);
        continue;
      }
      try {
        const token = await getToken();
        if (!token) throw new Error("Your session expired. Please sign in again.");
        setUploading({ name: file.name, size: file.size, percent: 0 });
        const uploaded = await uploadReport(file, sessionId, token, (percent) =>
          setUploading({ name: file.name, size: file.size, percent })
        );
        queryClient.setQueryData<Report[]>(["reports", sessionId], (curr) => [
          uploaded,
          ...(curr ?? []).filter((r) => r.id !== uploaded.id),
        ]);
        await queryClient.invalidateQueries({ queryKey: ["reports", sessionId] });
      } catch (reason) {
        setUploadError(reason instanceof Error ? reason.message : "Could not upload report.");
        setRetryFile(file);
      } finally {
        setUploading(null);
      }
    }
  }

  async function setLanguage(mode: LanguageMode) {
    try {
      await api(`/ai/language-mode`, (await getToken()) ?? "", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, mode }),
      });
      await queryClient.invalidateQueries({ queryKey: ["session-memory", sessionId] });
    } catch {
      setError("Could not save language preference.");
    }
  }

  async function submitHospitalLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const city = hospitalLocation.city.trim();
    if (!city) return;
    const details = [city, hospitalLocation.region.trim(), hospitalLocation.location.trim(), hospitalLocation.postal_code.trim()].filter(Boolean).join(", ");
    const succeeded = await ask(`My location is ${details}. Please recommend suitable hospitals for the condition in my reports.`, {
      city,
      region: hospitalLocation.region.trim() || undefined,
      location: hospitalLocation.location.trim() || undefined,
      postal_code: hospitalLocation.postal_code.trim() || undefined,
    });
    if (succeeded) {
      setHospitalLocationNeeded(false);
      setHospitalLocation({ city: "", region: "", location: "", postal_code: "" });
    }
  }

  async function downloadExport(format: "pdf" | "txt") {
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/export/${format}/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Could not create clinical export.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `medassist-clinical-export.${format}`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Clinical export failed.");
    }
  }

  async function sendEmailShare(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setEmailBusy(true);
    setError("");
    setEmailSuccess(false);
    try {
      await api("/share/email", (await getToken()) ?? "", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          recipient_email: emailAddress,
          include_report_summaries: includeSummaries,
        }),
      });
      setEmailSuccess(true);
      setTimeout(() => {
        setShareModalOpen(false);
        setEmailAddress("");
        setEmailSuccess(false);
      }, 1500);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Email delivery failed.");
    } finally {
      setEmailBusy(false);
    }
  }

  async function finishVoice(blob: Blob) {
    setTranscribing(true);
    setVoiceDone(false);
    setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      const extension = blob.type.includes("mp4") ? "mp4" : "webm";
      const form = new FormData();
      form.append("session_id", sessionId);
      form.append("file", new File([blob], `voice-input.${extension}`, { type: blob.type || "audio/webm" }));
      const response = await fetch(`${API_BASE}/ai/voice`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
        cache: "no-store",
      });
      if (!response.ok) {
        let detail = "Could not transcribe audio recording.";
        try {
          detail = (await response.json()).detail ?? detail;
        } catch {}
        throw new Error(detail);
      }
      const result = (await response.json()) as { text: string };
      setTranscribing(false);
      setDraft(result.text);
      if (await ask(result.text)) {
        setVoiceDone(true);
        window.setTimeout(() => setVoiceDone(false), 3000);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Voice transcription failed.");
    } finally {
      setTranscribing(false);
    }
  }

  async function startRecording() {
    setError("");
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        throw new Error("Voice recording is not supported in this browser.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      });
      streamRef.current = stream;
      chunksRef.current = [];
      const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((type) =>
        MediaRecorder.isTypeSupported(type)
      );
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunksRef.current.push(e.data);
      };
      recorder.onerror = () => {
        recorder.onstop = null;
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setRecording(false);
        setError("Microphone recording was interrupted.");
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        if (blob.size) void finishVoice(blob);
      };
      setRecordingSeconds(0);
      setVoiceDone(false);
      recorder.start();
      setRecording(true);
    } catch (reason) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setRecording(false);
      setError(reason instanceof Error ? reason.message : "Microphone access unavailable.");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function ask(rawQuestion: string, location?: HospitalLocation): Promise<boolean> {
    const question = rawQuestion.trim();
    if (!question || busy) return false;
    if (!reportsReady || uploading) {
      setError("Please wait for report processing to finish before querying.");
      return false;
    }
    setDraft("");
    setError("");
    setBusy(true);
    setLiveTurn({ question, answer: "", citations: [], medicalCitations: [] });
    const controller = new AbortController();
    generationControllerRef.current = controller;

    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/ai/chat`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ session_id: sessionId, question, ...(location ? { location } : {}) }),
        signal: controller.signal,
        cache: "no-store",
      });

      if (!response.ok || !response.body) {
        let msg = "Could not initialize response.";
        try {
          msg = (await response.json()).detail ?? msg;
        } catch {}
        throw new Error(msg);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamError = "";

      const consume = (frame: string) => {
        const data = frame
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim())
          .join("\n");
        if (!data) return;
        const ev = JSON.parse(data) as { type: string; content?: string; citations?: Citation[]; medical_citations?: Citation[]; message?: string };
        if (ev.type === "location_request") setHospitalLocationNeeded(true);
        if (ev.type === "citations") {
          setLiveTurn((curr) => (curr ? { ...curr, citations: ev.citations ?? [] } : curr));
        }
        if (ev.type === "medical_citations") {
          setLiveTurn((curr) => (curr ? { ...curr, medicalCitations: ev.citations ?? [] } : curr));
        }
        if (ev.type === "token" && ev.content) {
          setLiveTurn((curr) => (curr ? { ...curr, answer: curr.answer + ev.content } : curr));
        }
        if (ev.type === "error") streamError = ev.message ?? "Could not complete synthesis.";
      };

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) consume(frame);
        if (done) break;
      }
      if (buffer.trim()) consume(buffer);
      if (streamError) throw new Error(streamError);

      await queryClient.invalidateQueries({ queryKey: ["messages", sessionId] });
      setLiveTurn(null);
      return true;
    } catch (reason) {
      setError(
        reason instanceof DOMException && reason.name === "AbortError"
          ? "Response stopped. The partial answer was not saved."
          : reason instanceof Error
            ? reason.message
            : "Could not complete response."
      );
      await queryClient.invalidateQueries({ queryKey: ["messages", sessionId] });
      setLiveTurn(null);
      return false;
    } finally {
      if (generationControllerRef.current === controller) generationControllerRef.current = null;
      setBusy(false);
    }
  }

  function stopGeneration() {
    generationControllerRef.current?.abort();
  }

  function handleComposerKeyDown(e: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void ask(draft);
    }
  }

  const hasMessages = Boolean(messages.data?.length || liveTurn);

  return (
    <div
      className="relative flex flex-col flex-1 h-full min-h-screen"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (e.dataTransfer.files?.length) void handleFiles(e.dataTransfer.files);
      }}
    >
      {/* Hidden File Input */}
      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        multiple
        className="sr-only"
        onChange={(e) => {
          if (e.target.files?.length) void handleFiles(e.target.files);
          e.currentTarget.value = "";
        }}
      />

      {/* TOP WORKSPACE HEADER */}
      <header className={`fixed left-2 right-2 sm:left-4 sm:right-4 ${sidebarOpen ? "md:left-[18rem]" : "md:left-20"} top-3 sm:top-4 h-14 sm:h-16 bg-[#0e0e11]/90 backdrop-blur-xl border border-white/15 shadow-[0_8px_32px_0_rgba(0,0,0,0.5),0_0_20px_1px_rgba(255,255,255,0.08),inset_0_1px_0_0_rgba(255,255,255,0.2)] z-30 flex items-center justify-between gap-2 px-3 sm:px-6 rounded-2xl`}>
        {/* Left: Active title & report indicator */}
        <div className="flex items-center gap-space-md min-w-0">
          <div className="flex items-center gap-space-xs min-w-0">
            <span className="material-symbols-outlined text-secondary text-[20px] shrink-0">vital_signs</span>
            <span className="font-headline-sm text-[16px] font-medium text-primary tracking-tight truncate">
              {title}
            </span>
          </div>

        </div>

        {/* Right Action buttons */}
        <div className="flex items-center gap-space-sm shrink-0">
          {/* Health tools & language toggle */}
          <button
            onClick={() => setToolsOpen(!toolsOpen)}
            className="flex items-center gap-space-xs px-space-sm py-space-xs rounded-lg text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface border border-glass-border transition-all font-body-sm text-[13px]"
            type="button"
            title="Clinical Tools & Language"
          >
            <span className="material-symbols-outlined text-[18px] text-accent-chroma">tune</span>
            <span className="hidden sm:inline">Tools</span>
          </button>

          {/* Share Modal Trigger */}
          <button
            onClick={() => setShareModalOpen(true)}
            className="flex items-center gap-space-xs px-space-sm py-space-xs rounded-lg text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface border border-glass-border transition-all font-body-sm text-[13px]"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">ios_share</span>
            <span className="hidden sm:inline">Share</span>
          </button>

          {/* Export PDF Button */}
          <button
            onClick={() => void downloadExport("pdf")}
            className="flex items-center gap-space-xs px-space-sm py-space-xs rounded-lg text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface border border-glass-border transition-all font-body-sm text-[13px]"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
            <span className="hidden sm:inline">Export PDF</span>
          </button>
        </div>
      </header>

      {/* HEALTH TOOLS & LANGUAGE DRAWER */}
      {toolsOpen && (
        <div className="fixed top-20 sm:top-24 right-3 sm:right-10 z-50 w-96 max-w-[calc(100vw-1.5rem)] max-h-[calc(100dvh-6rem)] overflow-y-auto soft-scroll rounded-2xl bg-surface-container-low/95 border border-glass-border backdrop-blur-2xl p-4 sm:p-5 shadow-2xl space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-glass-border">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-primary">tune</span>
              <span className="font-headline-sm text-sm text-primary font-medium">Clinical Tools &amp; Settings</span>
            </div>
            <button onClick={() => setToolsOpen(false)} className="text-outline hover:text-primary">
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>

          {/* Language Mode */}
          <div className="space-y-1.5">
            <label className="font-label-code text-caption text-text-highlight uppercase">Response Language</label>
            <div className="grid grid-cols-2 gap-2">
              {(["auto", "english", "kannada", "bilingual"] as LanguageMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => void setLanguage(mode)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-label-code transition-all ${
                    languageMode === mode
                      ? "bg-primary text-background-canvas font-medium shadow-[0_0_12px_rgba(206,204,220,0.3)]"
                      : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  {mode === "auto"
                    ? "Auto Detect"
                    : mode === "kannada"
                    ? "ಕನ್ನಡ (Kannada)"
                    : mode === "bilingual"
                    ? "English + ಕನ್ನಡ"
                    : "English"}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 border-t border-glass-border pt-3">
            <button type="button" disabled={busy} onClick={() => { setToolsOpen(false); void ask(languageMode === "kannada" ? "ನನ್ನ ವರದಿಯನ್ನು ನೋಡಿ, ಯಾವ ಆಹಾರವನ್ನು ತಿನ್ನಬೇಕು ಮತ್ತು ಯಾವುದನ್ನು ತಪ್ಪಿಸಬೇಕು ಎಂದು ತಿಳಿಸಿ." : "Please review my medical report and suggest foods I should include or avoid."); }} className="w-full rounded-xl bg-surface-container px-3 py-2.5 text-left text-xs text-on-surface hover:bg-surface-container-high disabled:opacity-50">
              <span className="block font-medium">{languageMode === "kannada" ? "ಆಹಾರದ ಸಲಹೆಗಳು" : languageMode === "bilingual" ? "Food suggestions / ಆಹಾರದ ಸಲಹೆಗಳು" : "Food suggestions"}</span>
              <span className="mt-1 block text-on-surface-variant">{languageMode === "kannada" ? "ನಿಮ್ಮ ವರದಿ ಮತ್ತು ಲಕ್ಷಣಗಳ ಆಧಾರದ ಮೇಲೆ" : "Based on your report and symptoms"}</span>
            </button>
            <button type="button" disabled={busy} onClick={() => { setToolsOpen(false); void ask(languageMode === "kannada" ? "ನನ್ನ ವರದಿ ಅಥವಾ ಲಕ್ಷಣಗಳ ಆಧಾರದ ಮೇಲೆ ಸೂಕ್ತ ವೈದ್ಯರು ಅಥವಾ ಆಸ್ಪತ್ರೆಯನ್ನು ಸೂಚಿಸಿ." : "Please recommend a suitable doctor or hospital based on my report or symptoms."); }} className="w-full rounded-xl bg-surface-container px-3 py-2.5 text-left text-xs text-on-surface hover:bg-surface-container-high disabled:opacity-50">
              <span className="block font-medium">{languageMode === "kannada" ? "ವೈದ್ಯರು / ಆಸ್ಪತ್ರೆ ಹುಡುಕಿ" : languageMode === "bilingual" ? "Find a doctor or hospital / ವೈದ್ಯರು ಅಥವಾ ಆಸ್ಪತ್ರೆ" : "Find a doctor or hospital"}</span>
              <span className="mt-1 block text-on-surface-variant">{languageMode === "kannada" ? "ಮೊದಲು ವರದಿಯ ಸ್ಥಿತಿ ಅಥವಾ ನಿಮ್ಮ ಲಕ್ಷಣಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತದೆ" : "Checks report findings or asks about symptoms first"}</span>
            </button>
          </div>

          {/* Manage Reports Trigger */}
          <div className="pt-2 border-t border-glass-border">
            <button
              onClick={() => {
                setToolsOpen(false);
                setReportsModalOpen(true);
              }}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-surface-secondary/50 hover:bg-surface-secondary text-xs text-primary transition-all"
            >
              <span className="material-symbols-outlined text-[16px]">folder_open</span>
              {languageMode === "kannada" ? `ವರದಿಗಳು ಮತ್ತು ಸಾರಾಂಶಗಳನ್ನು ನಿರ್ವಹಿಸಿ (${reports.data?.length ?? 0})` : languageMode === "bilingual" ? `Manage Reports & Summaries / ವರದಿಗಳು (${reports.data?.length ?? 0})` : `Manage Reports & Summaries (${reports.data?.length ?? 0})`}
            </button>
          </div>
        </div>
      )}

      {/* ERROR DISPLAY */}
      {error && (
        <div className="pt-24 px-8 max-w-4xl mx-auto w-full z-10">
          <div className="p-3 rounded-xl bg-error-container/40 border border-error text-error text-xs flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError("")} className="material-symbols-outlined text-[16px]">close</button>
          </div>
        </div>
      )}

      {/* MAIN SCROLLABLE MESSAGE STREAM */}
      <main className="flex-1 overflow-y-auto px-6 lg:px-margin-lg pt-24 pb-48 w-full max-w-5xl mx-auto space-y-8 soft-scroll">
        {/* Loading state */}
        {messages.isLoading && (
          <div className="space-y-4 py-8">
            <div className="h-16 w-2/3 ml-auto rounded-2xl bg-surface-container-low/50 animate-pulse border border-glass-border"></div>
            <div className="h-28 w-4/5 rounded-2xl bg-surface-container/50 animate-pulse border border-glass-border"></div>
          </div>
        )}

        {/* Empty state / Welcome view */}
        {!hasMessages && !messages.isLoading && (
          <div className="flex flex-col items-start gap-4 pt-4">
            <div className="flex items-start gap-4 w-full">
              <div className="relative flex-shrink-0 w-9 h-9 mt-0.5">
                <div className="absolute inset-0 rounded-full bg-accent-chroma/20 animate-ping opacity-60"></div>
                <div className="relative w-full h-full rounded-full bg-surface-secondary border border-glass-border flex items-center justify-center shadow-lg">
                  <span className="material-symbols-outlined text-text-primary text-[18px]">neurology</span>
                </div>
              </div>

              <div className="flex-1 bg-surface-container/40 border border-glass-border rounded-xl p-5 shadow-sm backdrop-blur-md">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-glass-border">
                  <span className="font-label-code text-caption text-text-highlight uppercase tracking-wider">
                    Clinical Intelligence Core
                  </span>
                  <span className="font-caption text-caption text-surface-muted">Private conversation</span>
                </div>
                <p className="font-body-md text-body-md text-text-primary leading-relaxed">
                  Welcome to MedAssist AI. I am your intelligent clinical companion. You can upload laboratory reports, MRI analyses, or ask any medical question in plain language.
                </p>
                <div className="mt-4 flex flex-wrap gap-2 pt-2">
                  {[
                    "Summarize my report",
                    "Explain this test result",
                    "What medicines are listed?",
                    "What should I ask my clinician?",
                    "Answer in Kannada",
                  ].map((promptText) => (
                    <button
                      key={promptText}
                      onClick={() => void ask(promptText)}
                      className="px-3 py-1 rounded-full bg-surface-secondary/40 hover:bg-surface-secondary/80 border border-glass-border text-text-highlight font-label-code text-caption transition-colors"
                    >
                      {promptText}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Render historical messages */}
        {messages.data?.map((msg) => (
          <div key={msg.id} className="space-y-4">
            {msg.role === "user" ? (
              <div className="flex w-fit max-w-[min(100%,42rem)] items-start justify-end gap-3 ml-auto">
                <div className="w-fit max-w-[calc(100%-2.75rem)] bg-surface-secondary/50 border border-glass-border rounded-xl px-4 py-3 shadow-md backdrop-blur-md">
                  <div className="flex items-center justify-end gap-2 pb-1.5 mb-1.5 border-b border-glass-border">
                    <span className="font-caption text-caption text-surface-muted">Clinician / Patient</span>
                    <span className="material-symbols-outlined text-[14px] text-accent-chroma">done_all</span>
                  </div>
                  <p className="font-body-md text-body-md text-primary leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </p>
                </div>
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-surface-container-high border border-glass-border flex items-center justify-center text-text-highlight mt-1 shadow-inner">
                  <span className="material-symbols-outlined text-[16px]">person</span>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-4 max-w-4xl">
                <div className="relative shrink-0 mt-1">
                  <div className="w-10 h-10 rounded-full bg-surface-container-high border border-glass-border flex items-center justify-center text-primary shadow-[0_0_24px_rgba(109,113,138,0.25)] relative overflow-hidden">
                    <span className="material-symbols-outlined text-[20px] text-secondary">biotech</span>
                  </div>
                </div>

                <div className="flex flex-col flex-1 gap-space-md">
                  <div className="p-space-lg rounded-2xl bg-surface-container-lowest/80 border border-glass-border backdrop-blur-2xl shadow-xl flex flex-col gap-space-sm">
                    {/* Assistant metadata & actions */}
                    <div className="flex items-center justify-between pb-2 border-b border-glass-border">
                      <div className="flex items-center gap-2">
                        <span className="font-headline-sm text-[15px] font-medium text-primary">
                          MedAssist Clinical Engine
                        </span>
                        <span className="font-label-code text-[10px] bg-secondary-container/40 text-secondary px-2 py-0.5 rounded-full uppercase tracking-wider">
                          {msg.citations?.some((citation) => citation.source_type === "medical_knowledge")
                            ? "Verified Sources"
                            : msg.citations?.length ? "Report Grounded" : "General Information"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-outline">
                        <button
                          onClick={() => {
                            if (typeof window !== "undefined" && window.speechSynthesis) {
                              window.speechSynthesis.cancel();
                              const utterance = new SpeechSynthesisUtterance(cleanAssistantText(msg.content));
                              utterance.lang = /[\u0C80-\u0CFF]/.test(msg.content) ? "kn-IN" : "en-US";
                              window.speechSynthesis.speak(utterance);
                            }
                          }}
                          className="p-1 hover:text-primary transition-colors"
                          title="Listen to response"
                        >
                          <span className="material-symbols-outlined text-[18px]">volume_up</span>
                        </button>
                        <button
                          onClick={() => void navigator.clipboard.writeText(cleanAssistantText(msg.content))}
                          className="p-1 hover:text-primary transition-colors"
                          title="Copy response"
                        >
                          <span className="material-symbols-outlined text-[18px]">content_copy</span>
                        </button>
                      </div>
                    </div>

                    {/* Content text */}
                    <div className="font-body-md text-body-md text-text-primary leading-relaxed whitespace-pre-wrap">
                      {cleanAssistantText(msg.content)}
                    </div>

                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* LIVE TURN & REAL-TIME MULTI-AGENT THINKING PIPELINE */}
        {liveTurn && (
          <div className="space-y-4">
            {/* User question */}
            <div className="flex w-fit max-w-[min(100%,42rem)] items-start justify-end gap-3 ml-auto">
              <div className="w-fit max-w-[calc(100%-2.75rem)] bg-surface-secondary/50 border border-glass-border rounded-xl px-4 py-3 shadow-md backdrop-blur-md">
                <p className="font-body-md text-body-md text-primary leading-relaxed whitespace-pre-wrap">
                  {liveTurn.question}
                </p>
              </div>
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-surface-container-high border border-glass-border flex items-center justify-center text-text-highlight mt-1">
                <span className="material-symbols-outlined text-[16px]">person</span>
              </div>
            </div>

            {/* Thinking / Streaming pipeline card */}
            <div className="flex items-start gap-4 max-w-4xl">
              <div className="relative shrink-0 mt-1">
                <div className="w-10 h-10 rounded-full bg-surface-secondary border border-glass-border flex items-center justify-center text-primary shadow-[0_0_24px_rgba(109,113,138,0.35)] relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-tr from-accent-chroma/40 via-surface-tint/20 to-transparent animate-pulse"></div>
                  <span className="material-symbols-outlined text-[20px] relative z-10 text-primary">neurology</span>
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-secondary shadow-[0_0_8px_rgba(193,197,225,0.8)] animate-ping"></span>
              </div>

              <div className="flex flex-col flex-1 gap-space-md">
                <div role="status" aria-live="polite" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-surface-container-lowest/70 border border-glass-border backdrop-blur-2xl p-4 sm:p-space-lg shadow-xl">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="material-symbols-outlined text-secondary animate-spin" aria-hidden="true">progress_activity</span>
                    <div className="min-w-0">
                      <p className="font-headline-sm text-sm font-semibold text-primary">{liveTurn.answer ? "Writing your response" : "Preparing your response"}</p>
                      <p className="font-caption text-caption text-on-surface-variant mt-1">
                        {liveTurn.answer ? "The answer is streaming as it is generated." : hasReports ? "Checking the conversation and available report context." : "Processing your question."}
                      </p>
                    </div>
                  </div>
                  <button type="button" onClick={stopGeneration} className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-glass-border bg-surface-container-high px-3 py-2 text-xs text-primary hover:bg-surface-container-highest focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-chroma">
                    <span className="material-symbols-outlined text-[16px]" aria-hidden="true">stop_circle</span>
                    Stop response
                  </button>
                </div>

                {/* Live streaming text */}
                {liveTurn.answer && (
                  <div className="p-space-lg rounded-2xl bg-surface-container-lowest/80 border border-glass-border backdrop-blur-2xl shadow-xl flex flex-col gap-space-sm">
                    <p className="font-body-md text-body-md text-text-primary leading-relaxed whitespace-pre-wrap">
                      {cleanAssistantText(liveTurn.answer)}
                      <span className="ml-1 inline-block h-4 w-1 animate-pulse rounded bg-primary align-middle" />
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <footer aria-label="Medical information disclaimer" className="mx-auto max-w-3xl border-t border-glass-border pt-4 pb-2 text-center text-xs leading-relaxed text-on-surface-variant">
          {languageMode === "kannada" || (languageMode === "auto" && /[\u0C80-\u0CFF]/.test(lastUserQuestion)) ? (
            "MedAssist ನಿಮ್ಮ ವರದಿಗಳಲ್ಲಿನ ಮಾಹಿತಿ ಮತ್ತು ಸಾಮಾನ್ಯ ಆರೋಗ್ಯ ಶಿಕ್ಷಣವನ್ನು ಒದಗಿಸುತ್ತದೆ. ಇದು ವೃತ್ತಿಪರ ವೈದ್ಯಕೀಯ ಸಲಹೆಗೆ ಪರ್ಯಾಯವಲ್ಲ. ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಲ್ಲಿ ಸ್ಥಳೀಯ ತುರ್ತು ಸೇವೆಗಳನ್ನು ಸಂಪರ್ಕಿಸಿ."
          ) : languageMode === "bilingual" ? (
            <>{MEDICAL_DISCLAIMER_EN}<br />{MEDICAL_DISCLAIMER_KN}</>
          ) : (
            MEDICAL_DISCLAIMER_EN
          )}
        </footer>
      </main>

      {/* FLOATING GLASS COMPOSER (Bottom Centered Dock) */}
      <div className={`fixed bottom-3 sm:bottom-6 left-0 ${sidebarOpen ? "md:left-72" : "md:left-16"} right-0 px-3 sm:px-gutter pointer-events-none z-40 flex flex-col items-center`}>
        <div className="w-full max-w-4xl flex flex-col gap-2.5 pointer-events-auto">
          {hospitalLocationNeeded && (
            <form onSubmit={(event) => void submitHospitalLocation(event)} className="rounded-2xl bg-surface-container-low/95 border border-glass-border p-3 sm:p-4 shadow-xl backdrop-blur-xl space-y-3">
              <div>
                <p className="text-sm font-medium text-primary">Which city are you currently in?</p>
                <p className="mt-1 text-xs text-on-surface-variant">City is required. Add an area or PIN code to rank nearby directory listings.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input required minLength={2} maxLength={120} autoComplete="address-level2" placeholder="City (required)" value={hospitalLocation.city} onChange={(event) => setHospitalLocation((value) => ({ ...value, city: event.target.value }))} className="rounded-lg bg-surface-container-lowest px-3 py-2 text-sm text-primary border border-glass-border focus:outline-none focus:ring-1 focus:ring-accent-chroma" />
                <input maxLength={120} autoComplete="address-level1" placeholder="Region / district (optional)" value={hospitalLocation.region} onChange={(event) => setHospitalLocation((value) => ({ ...value, region: event.target.value }))} className="rounded-lg bg-surface-container-lowest px-3 py-2 text-sm text-primary border border-glass-border focus:outline-none focus:ring-1 focus:ring-accent-chroma" />
                <input maxLength={240} placeholder="Local area (optional)" value={hospitalLocation.location} onChange={(event) => setHospitalLocation((value) => ({ ...value, location: event.target.value }))} className="rounded-lg bg-surface-container-lowest px-3 py-2 text-sm text-primary border border-glass-border focus:outline-none focus:ring-1 focus:ring-accent-chroma" />
                <input maxLength={16} inputMode="numeric" autoComplete="postal-code" placeholder="PIN code (optional)" value={hospitalLocation.postal_code} onChange={(event) => setHospitalLocation((value) => ({ ...value, postal_code: event.target.value }))} className="rounded-lg bg-surface-container-lowest px-3 py-2 text-sm text-primary border border-glass-border focus:outline-none focus:ring-1 focus:ring-accent-chroma" />
              </div>
              <div className="flex justify-end">
                <button disabled={busy || !hospitalLocation.city.trim()} type="submit" className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-background-canvas disabled:opacity-50">
                  <span className="material-symbols-outlined text-sm">search</span>Find suitable hospitals
                </button>
              </div>
            </form>
          )}
          {/* Active Report Badge Chip on Composer */}
          {activeReport && (
            <div className="flex items-center justify-between px-4 py-1.5 rounded-full bg-[#18181c]/80 backdrop-blur-2xl self-start shadow-md border border-white/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px] text-error">picture_as_pdf</span>
                <span className="font-label-code text-caption text-primary">{activeReport.file_name}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_8px_rgba(193,197,225,0.6)]"></span>
                <span className="font-caption text-caption text-outline">
                  {reportStatus(activeReport)}
                </span>
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploading && (
            <div role="status" aria-live="polite" className="px-4 py-2 rounded-xl bg-surface-container-high/90 border border-glass-border backdrop-blur-md space-y-2 text-xs">
              <div className="flex items-center justify-between gap-3">
                <span className="min-w-0 truncate text-primary">Uploading {uploading.name} · {uploading.name.split(".").pop()?.toUpperCase()} · {(uploading.size / (1024 * 1024)).toFixed(1)} MB</span>
                <span className="font-label-code text-secondary">{uploading.percent}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-black/40"><div className="h-full rounded-full bg-secondary transition-[width] duration-200" style={{ width: `${uploading.percent}%` }} /></div>
            </div>
          )}
          {uploadError && (
            <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-error/50 bg-error-container/30 px-4 py-2 text-xs text-error">
              <span className="min-w-0">{uploadError}</span>
              <div className="flex shrink-0 items-center gap-3">
                {retryFile && <button type="button" onClick={() => void handleFiles([retryFile])} className="underline">Retry upload</button>}
                <button type="button" aria-label="Dismiss upload error" onClick={() => setUploadError("")} className="material-symbols-outlined text-base">close</button>
              </div>
            </div>
          )}

          {/* Composer Capsule */}
          <div className="relative w-full rounded-[36px] bg-[#121216]/75 backdrop-blur-2xl p-2.5 px-3.5 shadow-[0_20px_50px_rgba(0,0,0,0.7),0_0_30px_rgba(185,182,202,0.08)] border border-white/15 flex items-end gap-2.5">
            {/* Attachment Button */}
            <div className="relative">
              <button
                onClick={() => setAttachmentMenuOpen(!attachmentMenuOpen)}
                className="w-10 h-10 rounded-full bg-surface-container/80 flex items-center justify-center text-text-primary hover:bg-surface-container-high hover:text-white transition-all shadow-sm border border-glass-border"
                type="button"
                title="Attach Clinical Records"
              >
                <span className="material-symbols-outlined text-[20px]">add</span>
              </button>

              {/* Attachment Popover */}
              {attachmentMenuOpen && (
                <div className="absolute bottom-12 left-0 w-64 rounded-2xl bg-surface-container-high/95 border border-glass-border backdrop-blur-2xl p-2 shadow-2xl flex flex-col gap-1 z-50">
                  <button
                    onClick={() => fileInput.current?.click()}
                    className="flex items-center gap-2.5 px-3 py-2 text-left rounded-xl hover:bg-surface-container-highest transition-colors group"
                    type="button"
                  >
                    <span className="material-symbols-outlined text-error text-[18px]">picture_as_pdf</span>
                    <div className="flex flex-col">
                      <span className="font-body-sm text-body-sm font-medium text-primary">Upload Lab PDF / Image</span>
                      <span className="font-caption text-caption text-outline">OCR parsing &amp; indexing</span>
                    </div>
                  </button>
                  <button
                    onClick={() => {
                      setAttachmentMenuOpen(false);
                      setReportsModalOpen(true);
                    }}
                    className="flex items-center gap-2.5 px-3 py-2 text-left rounded-xl hover:bg-surface-container-highest transition-colors group"
                    type="button"
                  >
                    <span className="material-symbols-outlined text-secondary text-[18px]">folder_open</span>
                    <div className="flex flex-col">
                      <span className="font-body-sm text-body-sm font-medium text-primary">View Attached Reports</span>
                      <span className="font-caption text-caption text-outline">Manage active documents</span>
                    </div>
                  </button>
                </div>
              )}
            </div>

            {/* Input Textarea */}
            <textarea
              ref={composerRef}
              rows={1}
              value={draft}
              onChange={(e) => {
                setDraft(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = `${e.target.scrollHeight}px`;
              }}
              onKeyDown={handleComposerKeyDown}
              disabled={busy || recording || transcribing}
              placeholder="Ask MedAssist AI... (e.g. explain medication contraindications or lipid targets)"
              className="flex-1 bg-transparent px-3 py-2.5 max-h-36 resize-none font-body-md text-body-md text-primary placeholder:text-surface-muted focus:outline-none"
            />

            {/* Right Action Buttons: Mic & Send */}
            <div className="flex items-center gap-1.5 pb-0.5">
              <button
                onClick={() => (recording ? stopRecording() : void startRecording())}
                disabled={busy || transcribing}
                className={`w-10 h-10 rounded-full flex items-center justify-center transition-all relative border border-glass-border ${
                  recording
                    ? "bg-error text-background-canvas animate-pulse"
                    : "bg-surface-container/80 text-text-primary hover:bg-surface-container-high"
                }`}
                type="button"
                title={recording ? `Recording ${recordingSeconds}s - click to stop` : "Voice Dictation"}
              >
                <span className="material-symbols-outlined text-[20px]">{recording ? "mic_off" : "mic"}</span>
              </button>

              {busy ? (
                <button onClick={stopGeneration} className="w-10 h-10 rounded-full bg-error text-background-canvas flex items-center justify-center hover:bg-error/80 transition-all" type="button" title="Stop response" aria-label="Stop response">
                  <span className="material-symbols-outlined text-[20px]">stop</span>
                </button>
              ) : (
                <button
                  onClick={() => void ask(draft)}
                  disabled={recording || transcribing || !draft.trim() || !reportsReady}
                  className="w-10 h-10 rounded-full bg-primary text-background-canvas flex items-center justify-center hover:bg-white hover:shadow-[0_0_20px_rgba(206,204,220,0.35)] transition-all font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
                  type="button"
                  title="Send inquiry"
                  aria-label="Send inquiry"
                >
                  <span className="material-symbols-outlined text-[20px]">arrow_upward</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* EXPORT & SHARE MODAL */}
      {shareModalOpen && (
        <div role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setShareModalOpen(false); }} className="fixed inset-0 z-50 bg-background-canvas/70 backdrop-blur-md flex items-center justify-center p-3 sm:p-space-md">
          <div role="dialog" aria-modal="true" aria-labelledby="share-dialog-title" className="w-full max-w-lg max-h-[90dvh] overflow-y-auto soft-scroll rounded-2xl bg-surface-container-low/95 border border-glass-border backdrop-blur-3xl p-4 sm:p-space-xl shadow-[0_24px_64px_rgba(0,0,0,0.9)] flex flex-col gap-4 sm:gap-space-lg relative">
            <div className="flex items-center justify-between pb-2 border-b border-glass-border">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary text-[22px]">download_for_offline</span>
                  <span id="share-dialog-title" className="font-headline-sm text-headline-sm text-primary font-medium">
                  Share or export conversation
                </span>
              </div>
              <button type="button" aria-label="Close share dialog" onClick={() => setShareModalOpen(false)} className="text-outline hover:text-primary p-1">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <p className="font-body-md text-body-md text-text-primary">
              Share this conversation by email or download its saved messages, citations, report names, and recommendations.
            </p>

            {/* Export format choices */}
            <div className="flex flex-col gap-space-sm">
              <label
                onClick={() => setExportFormat("pdf")}
                className={`flex items-center justify-between p-3 rounded-xl border border-glass-border cursor-pointer transition-colors ${
                  exportFormat === "pdf" ? "bg-surface-container-high border-secondary/40" : "bg-surface-container"
                }`}
              >
                <div className="flex flex-col">
                  <span className="font-body-sm text-body-sm font-medium text-primary">PDF document</span>
                  <span className="font-caption text-caption text-outline">
                    Formatted conversation export
                  </span>
                </div>
                <input
                  type="radio"
                  checked={exportFormat === "pdf"}
                  onChange={() => setExportFormat("pdf")}
                  className="accent-secondary"
                />
              </label>

              <label
                onClick={() => setExportFormat("txt")}
                className={`flex items-center justify-between p-3 rounded-xl border border-glass-border cursor-pointer transition-colors ${
                  exportFormat === "txt" ? "bg-surface-container-high border-secondary/40" : "bg-surface-container"
                }`}
              >
                <div className="flex flex-col">
                  <span className="font-body-sm text-body-sm font-medium text-primary">Plain text</span>
                  <span className="font-caption text-caption text-outline">
                    Lightweight, readable transcript
                  </span>
                </div>
                <input
                  type="radio"
                  checked={exportFormat === "txt"}
                  onChange={() => setExportFormat("txt")}
                  className="accent-secondary"
                />
              </label>
            </div>

            {/* Email Share Form */}
            <form onSubmit={sendEmailShare} className="space-y-2 pt-2 border-t border-glass-border">
              <label className="font-label-code text-caption text-text-highlight uppercase block">
                Share via email
              </label>
              <div className="flex gap-2">
                <input
                  type="email"
                  required
                  placeholder="physician@clinic.org"
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-xl bg-surface-container-lowest border border-glass-border text-xs text-primary focus:outline-none"
                />
                <button
                  disabled={emailBusy}
                  className="px-4 py-2 rounded-xl bg-surface-container-high text-primary hover:bg-surface-secondary text-xs transition-all"
                >
                  {emailBusy ? "Sending..." : "Send Email"}
                </button>
              </div>
              {emailSuccess && <p className="text-xs text-secondary font-label-code">✓ Summary dispatched successfully.</p>}
            </form>

            {/* Actions */}
            <div className="flex items-center justify-end gap-space-sm pt-space-sm border-t border-glass-border">
              <button
                onClick={async () => {
                  try {
                    const link = new URL("/dashboard", window.location.origin);
                    link.searchParams.set("session_id", sessionId);
                    await navigator.clipboard.writeText(link.toString());
                    setCopiedLink(true);
                    window.setTimeout(() => setCopiedLink(false), 2000);
                  } catch {
                    setError("Could not copy the conversation link. Check browser clipboard permissions.");
                  }
                }}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-surface-container-high border border-glass-border text-primary hover:bg-surface-secondary font-body-sm text-body-sm transition-all"
              >
                <span className="material-symbols-outlined text-[16px]">link</span>
                <span>{copiedLink ? "Link copied" : "Copy conversation link"}</span>
              </button>

              <button
                onClick={() => void downloadExport(exportFormat)}
                className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-primary text-background-canvas font-body-sm text-body-sm font-medium hover:bg-white hover:shadow-[0_0_20px_rgba(206,204,220,0.35)] transition-all"
              >
                <span className="material-symbols-outlined text-[16px]">download</span>
                <span>Download {exportFormat.toUpperCase()}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REPORTS PANEL MODAL */}
      {reportsModalOpen && (
        <div role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setReportsModalOpen(false); }} className="fixed inset-0 z-50 bg-background-canvas/75 backdrop-blur-md flex items-center justify-center p-3 sm:p-4">
          <div role="dialog" aria-modal="true" aria-label="Medical documents and OCR" className="w-full max-w-2xl max-h-[85dvh] rounded-2xl bg-surface-container-low/95 border border-glass-border backdrop-blur-3xl p-4 sm:p-6 shadow-2xl flex flex-col gap-4 overflow-hidden">
            <div className="flex items-center justify-between pb-2 border-b border-glass-border">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">folder_open</span>
                <span className="font-headline-sm text-base text-primary font-medium">Medical Documents &amp; OCR</span>
              </div>
              <button type="button" aria-label="Close medical documents" onClick={() => setReportsModalOpen(false)} className="text-outline hover:text-primary">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="overflow-y-auto flex-1 soft-scroll pr-1">
              <ReportsPanel sessionId={sessionId} getToken={getToken} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function isProcessing(report: Report) {
  return report.processing_status === "pending" || report.processing_status === "processing";
}

function reportStatus(report: Report) {
  if (report.processing_status === "completed") return "Context ready";
  if (report.processing_status === "failed") return "Processing failed";
  switch (report.processing_stage) {
    case "extracting_text": return "Extracting text";
    case "generating_embeddings": return "Generating embeddings";
    case "storing_vectors": return "Saving report index";
    case "processing": return "Starting processing";
    default: return "Queued";
  }
}

function cleanAssistantText(content: string) {
  return content
    .replace(/This information is based on uploaded documents and is not a substitute for professional medical advice\.?/gi, "")
    .replace(/This information is for general educational purposes and is not a substitute for professional medical advice\.?/gi, "")
    .replace(/These suggestions are informational,[^\n]*professional medical advice\.?[^\n]*/gi, "")
    .replace(/ಈ ಮಾಹಿತಿ (?:ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ದಾಖಲೆಗಳ ಆಧಾರದ ಮೇಲೆ ಮಾತ್ರವಾಗಿದ್ದು|ಸಾಮಾನ್ಯ ಶಿಕ್ಷಣಕ್ಕಾಗಿ ಮಾತ್ರ)[^\n]*ವೈದ್ಯಕೀಯ ಸಲಹೆಗೆ ಪರ್ಯಾಯವಲ್ಲ\.?/g, "")
    .replace(/ಈ ಸಲಹೆಗಳು ಮಾಹಿತಿಗಾಗಿ ಮಾತ್ರ;[^\n]*ವೈದ್ಯಕೀಯ ಸಲಹೆಗೆ ಪರ್ಯಾಯವಲ್ಲ\.[^\n]*/g, "")
    .replace(/\s*\[(?:\d+(?:\s*[-,]\s*\d+)*)\](?=\s|[.,;:!?)]|$)/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

const MEDICAL_DISCLAIMER_EN = "MedAssist provides information from your reports and general health education. It is not a substitute for professional medical advice. For emergencies, contact local emergency services.";
const MEDICAL_DISCLAIMER_KN = "MedAssist ನಿಮ್ಮ ವರದಿಗಳಲ್ಲಿನ ಮಾಹಿತಿ ಮತ್ತು ಸಾಮಾನ್ಯ ಆರೋಗ್ಯ ಶಿಕ್ಷಣವನ್ನು ಒದಗಿಸುತ್ತದೆ. ಇದು ವೃತ್ತಿಪರ ವೈದ್ಯಕೀಯ ಸಲಹೆಗೆ ಪರ್ಯಾಯವಲ್ಲ. ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಲ್ಲಿ ಸ್ಥಳೀಯ ತುರ್ತು ಸೇವೆಗಳನ್ನು ಸಂಪರ್ಕಿಸಿ.";
