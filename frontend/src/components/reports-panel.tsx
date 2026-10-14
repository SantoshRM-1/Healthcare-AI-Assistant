"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Download, Eye, FileImage, FileText, LoaderCircle, Sparkles, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Report } from "@/lib/report-upload";

type Summary = {
  report_id: string; report_name: string; generated_at: string | null;
  summary: {
    patient_information: { name: string | null; age: string | null; date_of_birth: string | null; sex: string | null; other: string[] };
    diagnosis: string[];
    medicines: { name: string; dosage: string | null; frequency: string | null; route: string | null; notes: string | null }[];
    important_findings: string[]; recommendations: string[];
  };
};
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function ReportsPanel({ sessionId, getToken }: { sessionId: string; getToken: () => Promise<string | null> }) {
  const queryClient = useQueryClient();
  const previewUrl = useRef<string | null>(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<{ name: string; url: string } | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const reports = useQuery({
    queryKey: ["reports", sessionId],
    queryFn: async () => api<Report[]>(`/reports?session_id=${encodeURIComponent(sessionId)}`, (await getToken()) ?? ""),
    refetchInterval: query => query.state.data?.some(report => report.processing_status === "pending" || report.processing_status === "processing") ? 2_000 : false,
  });
  const remove = useMutation({
    mutationFn: async (reportId: string) => api<void>(`/reports/${reportId}`, (await getToken()) ?? "", { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", sessionId] }),
    onError: (reason: Error) => setError(reason.message),
  });
  const retry = useMutation({
    mutationFn: async (reportId: string) => api<Report>(`/reports/${reportId}/retry`, (await getToken()) ?? "", { method: "POST" }),
    onSuccess: report => queryClient.setQueryData<Report[]>(["reports", sessionId], current => [report, ...(current ?? []).filter(item => item.id !== report.id)]),
    onError: (reason: Error) => setError(reason.message),
  });

  async function showPreview(report: Report) {
    setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/reports/${report.id}/preview`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
      if (!response.ok) throw new Error("Could not open this report.");
      const url = URL.createObjectURL(await response.blob());
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
      previewUrl.current = url;
      setPreview({ name: report.file_name, url });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not open this report."); }
  }

  async function downloadReport(report: Report) {
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/reports/${report.id}/preview`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
      if (!response.ok) throw new Error("Could not download this report.");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = report.file_name; anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not download this report."); }
  }

  async function showSummary(report: Report) {
    setError(""); setSummaryLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      setSummary(await api<Summary>("/ai/report-summary", token, { method: "POST", body: JSON.stringify({ report_id: report.id }) }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create this report summary."); }
    finally { setSummaryLoading(false); }
  }

  const closePreview = useCallback(() => {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null; setPreview(null);
  }, []);
  useEffect(() => () => { if (previewUrl.current) URL.revokeObjectURL(previewUrl.current); }, []);
  useEffect(() => {
    if (!summary && !preview) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => { if (event.key === "Escape") { setSummary(null); closePreview(); } };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [summary, preview, closePreview]);

  return <details open={Boolean(reports.data?.some(report => report.processing_status === "failed"))} className="mt-4 rounded-2xl border border-slate-200 bg-white">
    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3.5 text-sm font-semibold text-slate-700">
      <span className="flex items-center gap-2"><FileText size={16} className="text-blue-600"/>Medical reports <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700">{reports.data?.length ?? 0}</span></span>
      <span className="text-xs font-normal text-slate-400">Manage files and summaries</span>
    </summary>
    <div className="space-y-2 border-t border-slate-100 p-3">
      {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-100 bg-rose-50 px-3 py-2.5 text-xs text-rose-700"><AlertCircle size={14} className="mt-0.5 shrink-0"/><span className="flex-1">{error}</span><button type="button" onClick={() => setError("")} aria-label="Dismiss error"><X size={14}/></button></div>}
      {reports.isLoading ? <div role="status" className="flex items-center justify-center gap-2 py-5 text-xs text-slate-400"><LoaderCircle size={15} className="animate-spin"/>Loading reports…</div>
        : reports.error ? <div role="alert" className="rounded-xl bg-rose-50 p-3 text-xs text-rose-700">Could not load reports. <button type="button" onClick={() => void reports.refetch()} className="font-semibold underline">Retry</button></div>
        : reports.data?.length ? reports.data.map(report => <article key={report.id} className="flex items-center gap-3 rounded-xl border border-slate-100 p-3 transition hover:border-blue-100 hover:bg-blue-50/20">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-blue-50 text-blue-600">{report.file_type === "application/pdf" ? <FileText size={17}/> : <FileImage size={17}/>}</span>
          <div className="min-w-0 flex-1"><div className="truncate text-xs font-semibold text-slate-700">{report.file_name}</div><div className="mt-1 flex flex-wrap items-center gap-x-2 text-[10px] text-slate-400"><span>{new Date(report.upload_date).toLocaleDateString()}</span><span>·</span><span>{(report.file_size / 1024 / 1024).toFixed(1)} MB</span><span>·</span><span className={report.processing_status === "completed" ? "text-emerald-600" : report.processing_status === "failed" ? "text-rose-600" : "text-blue-600"}>{report.processing_status === "completed" ? "✓ Ready" : report.processing_status === "failed" ? "Processing failed" : report.processing_stage === "extracting_text" ? "Extracting text…" : report.processing_stage === "generating_embeddings" ? "Generating embeddings…" : "Queued…"}</span></div>{(report.processing_status === "pending" || report.processing_status === "processing") && <div role="progressbar" aria-label={`Processing ${report.file_name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={report.processing_stage === "generating_embeddings" ? 70 : report.processing_stage === "extracting_text" ? 35 : 10} className="mt-2 h-1 overflow-hidden rounded-full bg-blue-100"><div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${report.processing_stage === "generating_embeddings" ? 70 : report.processing_stage === "extracting_text" ? 35 : 10}%` }}/></div>}</div>
          <div className="flex shrink-0 items-center gap-0.5">{report.processing_status === "failed" && <button type="button" onClick={() => retry.mutate(report.id)} disabled={retry.isPending} title="Retry processing" aria-label={`Retry processing ${report.file_name}`} className="rounded-lg px-2 py-1 text-[10px] font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-50">Retry</button>}<button type="button" onClick={() => void showSummary(report)} disabled={report.processing_status !== "completed" || summaryLoading} title="Summarize report" aria-label={`Summarize ${report.file_name}`} className="rounded-lg p-2 text-slate-400 hover:bg-violet-50 hover:text-violet-600 disabled:opacity-40"><Sparkles size={15}/></button><button type="button" onClick={() => void showPreview(report)} title="Preview report" aria-label={`Preview ${report.file_name}`} className="rounded-lg p-2 text-slate-400 hover:bg-blue-50 hover:text-blue-600"><Eye size={15}/></button><button type="button" onClick={() => void downloadReport(report)} title="Download report" aria-label={`Download ${report.file_name}`} className="rounded-lg p-2 text-slate-400 hover:bg-blue-50 hover:text-blue-600"><Download size={15}/></button><button type="button" onClick={() => remove.mutate(report.id)} disabled={remove.isPending} title="Delete report" aria-label={`Delete ${report.file_name}`} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"><Trash2 size={15}/></button></div>
        </article>) : <p className="rounded-xl border border-dashed border-slate-200 px-4 py-5 text-center text-xs text-slate-500">No reports attached yet. Use the + button in the composer to add one.</p>}
      {summaryLoading && <div role="status" className="flex items-center gap-2 rounded-xl bg-violet-50 px-3 py-3 text-xs font-medium text-violet-700"><LoaderCircle size={15} className="animate-spin"/>Preparing report summary…</div>}
    </div>
    {summary && <div role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setSummary(null); }} className="fixed inset-0 z-[101] flex items-center justify-center bg-slate-950/60 p-3 backdrop-blur-sm sm:p-8"><div role="dialog" aria-modal="true" aria-label={`${summary.report_name} summary`} className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"><div className="flex shrink-0 items-center justify-between border-b px-5 py-4"><div className="min-w-0"><div className="text-sm font-semibold">Report summary</div><p className="mt-1 truncate text-xs text-slate-500">{summary.report_name}</p></div><button type="button" onClick={() => setSummary(null)} aria-label="Close report summary" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X size={17}/></button></div><div className="soft-scroll space-y-5 overflow-y-auto p-5"><SummarySection title="Patient information"><div className="grid gap-2 text-xs sm:grid-cols-2">{[["Name", summary.summary.patient_information.name], ["Age", summary.summary.patient_information.age], ["Date of birth", summary.summary.patient_information.date_of_birth], ["Sex", summary.summary.patient_information.sex]].map(([label, value]) => <div key={label} className="rounded-lg bg-slate-50 px-3 py-2"><span className="text-slate-400">{label}</span><div className="mt-1 font-medium text-slate-700">{value || "Not stated in report"}</div></div>)}</div><SummaryList items={summary.summary.patient_information.other}/></SummarySection><SummarySection title="Diagnosis"><SummaryList items={summary.summary.diagnosis}/></SummarySection><SummarySection title="Medicines and dosage">{summary.summary.medicines.length ? summary.summary.medicines.map((medicine, index) => <div key={`${medicine.name}-${index}`} className="mb-2 rounded-xl border border-blue-100 bg-blue-50/40 p-3"><div className="text-xs font-semibold text-slate-700">{medicine.name}</div><p className="mt-1 text-xs text-slate-600">{[medicine.dosage, medicine.frequency, medicine.route].filter(Boolean).join(" · ") || "Dosage details not stated in report"}</p>{medicine.notes && <p className="mt-1 text-[11px] text-slate-500">{medicine.notes}</p>}</div>) : <SummaryList items={[]}/>}</SummarySection><SummarySection title="Important findings"><SummaryList items={summary.summary.important_findings}/></SummarySection><SummarySection title="Recommendations in report"><SummaryList items={summary.summary.recommendations}/></SummarySection><p className="border-t pt-3 text-[10px] leading-4 text-slate-400">This summary reflects the uploaded document and is not a substitute for professional medical advice.</p></div></div></div>}
    {preview && <div role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) closePreview(); }} className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 p-3 backdrop-blur-sm sm:p-8"><div role="dialog" aria-modal="true" aria-label={`Preview ${preview.name}`} className="flex h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"><div className="flex h-12 shrink-0 items-center justify-between border-b px-4"><span className="truncate pr-3 text-sm font-semibold">{preview.name}</span><button type="button" onClick={closePreview} aria-label="Close preview" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X size={17}/></button></div><iframe title={`Report preview: ${preview.name}`} src={preview.url} className="h-full w-full flex-1 bg-slate-100"/></div></div>}
  </details>;
}

function SummarySection({ title, children }: { title: string; children: React.ReactNode }) { return <section><h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</h3>{children}</section>; }
function SummaryList({ items }: { items: string[] }) { return items.length ? <ul className="space-y-1.5">{items.map((item, index) => <li key={`${item}-${index}`} className="flex gap-2 text-xs leading-5 text-slate-600"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-blue-500"/>{item}</li>)}</ul> : <p className="text-xs text-slate-400">Not stated in report.</p>; }
