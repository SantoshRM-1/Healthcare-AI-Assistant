"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Report } from "@/lib/report-upload";

type Summary = {
  report_id: string;
  report_name: string;
  generated_at: string | null;
  summary: {
    patient_information: {
      name: string | null;
      age: string | null;
      date_of_birth: string | null;
      sex: string | null;
      other: string[];
    };
    diagnosis: string[];
    medicines: {
      name: string;
      dosage: string | null;
      frequency: string | null;
      route: string | null;
      notes: string | null;
    }[];
    important_findings: string[];
    recommendations: string[];
  };
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function ReportsPanel({
  sessionId,
  getToken,
}: {
  sessionId: string;
  getToken: () => Promise<string | null>;
}) {
  const queryClient = useQueryClient();
  const previewUrl = useRef<string | null>(null);

  const [error, setError] = useState("");
  const [preview, setPreview] = useState<{ name: string; url: string } | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const reports = useQuery({
    queryKey: ["reports", sessionId],
    queryFn: async () => api<Report[]>(`/reports?session_id=${encodeURIComponent(sessionId)}`, (await getToken()) ?? ""),
    refetchInterval: (query) =>
      query.state.data?.some((report) => report.processing_status === "pending" || report.processing_status === "processing")
        ? 2_000
        : false,
  });

  const remove = useMutation({
    mutationFn: async (reportId: string) =>
      api<void>(`/reports/${reportId}`, (await getToken()) ?? "", { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", sessionId] }),
    onError: (reason: Error) => setError(reason.message),
  });

  const retry = useMutation({
    mutationFn: async (reportId: string) =>
      api<Report>(`/reports/${reportId}/retry`, (await getToken()) ?? "", { method: "POST" }),
    onSuccess: (report) =>
      queryClient.setQueryData<Report[]>(["reports", sessionId], (current) => [
        report,
        ...(current ?? []).filter((item) => item.id !== report.id),
      ]),
    onError: (reason: Error) => setError(reason.message),
  });

  async function showPreview(report: Report) {
    setError("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/reports/${report.id}/preview`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Could not open this report.");
      const url = URL.createObjectURL(await response.blob());
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
      previewUrl.current = url;
      setPreview({ name: report.file_name, url });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not open report.");
    }
  }

  async function downloadReport(report: Report) {
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      const response = await fetch(`${API_BASE}/reports/${report.id}/preview`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Could not download report.");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = report.file_name;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not download report.");
    }
  }

  async function showSummary(report: Report) {
    setError("");
    setSummaryLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Your session expired. Please sign in again.");
      setSummary(
        await api<Summary>("/ai/report-summary", token, {
          method: "POST",
          body: JSON.stringify({ report_id: report.id }),
        })
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create report summary.");
    } finally {
      setSummaryLoading(false);
    }
  }

  const closePreview = useCallback(() => {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
    setPreview(null);
  }, []);

  useEffect(() => () => {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
  }, []);

  useEffect(() => {
    if (!summary && !preview) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSummary(null);
        closePreview();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [summary, preview, closePreview]);

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 rounded-xl bg-error-container/40 border border-error text-error text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError("")} className="material-symbols-outlined text-[16px]">
            close
          </button>
        </div>
      )}

      {reports.isLoading ? (
        <div className="p-4 text-center text-xs text-outline flex items-center justify-center gap-2">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
          Loading documents...
        </div>
      ) : reports.error ? (
        <div className="p-3 text-xs text-error">Could not load documents.</div>
      ) : reports.data?.length ? (
        <div className="space-y-2">
          {reports.data.map((report) => (
            <div
              key={report.id}
              className="p-3.5 rounded-xl bg-surface-container/60 border border-glass-border flex items-center justify-between gap-3 hover:border-secondary/40 transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-lg bg-surface-container-high border border-glass-border flex items-center justify-center text-primary shrink-0">
                  <span className="material-symbols-outlined text-[20px] text-accent-chroma">
                    {report.file_type === "application/pdf" ? "picture_as_pdf" : "image"}
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-body-sm text-xs font-medium text-primary truncate max-w-sm">
                    {report.file_name}
                  </span>
                  <div className="flex items-center gap-2 font-caption text-caption text-outline">
                    <span>{(report.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                    <span>•</span>
                    <span
                      className={
                        report.processing_status === "completed"
                          ? "text-secondary font-label-code"
                          : report.processing_status === "failed"
                          ? "text-error font-label-code"
                          : "text-text-highlight font-label-code animate-pulse"
                      }
                    >
                      {processingLabel(report)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1">
                {report.processing_status === "failed" && (
                  <button
                    onClick={() => retry.mutate(report.id)}
                    className="px-2 py-1 rounded bg-secondary-container text-secondary text-xs hover:bg-secondary-container/80"
                  >
                    Retry
                  </button>
                )}
                {report.processing_status === "completed" && (
                  <button
                    onClick={() => void showSummary(report)}
                    disabled={summaryLoading}
                    className="p-1.5 rounded-lg text-outline hover:text-primary hover:bg-surface-container-high transition-colors"
                    title="Generate structured summary"
                  >
                    <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                  </button>
                )}
                <button
                  onClick={() => void showPreview(report)}
                  className="p-1.5 rounded-lg text-outline hover:text-primary hover:bg-surface-container-high transition-colors"
                  title="Preview document"
                >
                  <span className="material-symbols-outlined text-[18px]">visibility</span>
                </button>
                <button
                  onClick={() => void downloadReport(report)}
                  className="p-1.5 rounded-lg text-outline hover:text-primary hover:bg-surface-container-high transition-colors"
                  title="Download original"
                >
                  <span className="material-symbols-outlined text-[18px]">download</span>
                </button>
                <button
                  onClick={() => {
                    if (window.confirm(`Delete ${report.file_name}?`)) {
                      remove.mutate(report.id);
                    }
                  }}
                  className="p-1.5 rounded-lg text-outline hover:text-error hover:bg-error-container/30 transition-colors"
                  title="Delete report"
                >
                  <span className="material-symbols-outlined text-[18px]">delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-6 text-center text-xs text-outline border border-dashed border-glass-border rounded-xl">
          No medical records uploaded for this consultation.
        </div>
      )}

      {/* Structured Summary Modal */}
      {summary && (
        <div className="fixed inset-0 z-[101] bg-background-canvas/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[85vh] rounded-2xl bg-surface-container-low border border-glass-border backdrop-blur-3xl p-6 shadow-2xl flex flex-col gap-4 overflow-hidden">
            <div className="flex items-center justify-between pb-2 border-b border-glass-border">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary text-[20px]">assignment</span>
                <span className="font-headline-sm text-base text-primary font-medium">
                  Report Summary • {summary.report_name}
                </span>
              </div>
              <button onClick={() => setSummary(null)} className="text-outline hover:text-primary">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="overflow-y-auto flex-1 soft-scroll space-y-4 pr-1 text-xs">
              {/* Patient info */}
              <div className="p-3.5 rounded-xl bg-surface-container/60 border border-glass-border">
                <span className="font-label-code text-caption text-text-highlight uppercase block mb-2">
                  Patient Information
                </span>
                <div className="grid grid-cols-2 gap-2 text-text-primary">
                  <div>Name: {summary.summary.patient_information.name || "N/A"}</div>
                  <div>Age: {summary.summary.patient_information.age || "N/A"}</div>
                  <div>DOB: {summary.summary.patient_information.date_of_birth || "N/A"}</div>
                  <div>Sex: {summary.summary.patient_information.sex || "N/A"}</div>
                </div>
              </div>

              {/* Diagnosis */}
              {summary.summary.diagnosis.length > 0 && (
                <div className="p-3.5 rounded-xl bg-surface-container/60 border border-glass-border">
                  <span className="font-label-code text-caption text-text-highlight uppercase block mb-2">
                    Diagnoses &amp; Indications
                  </span>
                  <ul className="list-disc list-inside space-y-1 text-text-primary">
                    {summary.summary.diagnosis.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Medicines */}
              {summary.summary.medicines.length > 0 && (
                <div className="p-3.5 rounded-xl bg-surface-container/60 border border-glass-border">
                  <span className="font-label-code text-caption text-text-highlight uppercase block mb-2">
                    Medicines &amp; Regimen
                  </span>
                  <div className="space-y-1.5">
                    {summary.summary.medicines.map((m, i) => (
                      <div key={i} className="p-2 rounded-lg bg-surface-container-high/40 text-text-primary">
                        <strong className="text-primary">{m.name}</strong>
                        {m.dosage && <span> — {m.dosage}</span>}
                        {m.frequency && <span> ({m.frequency})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Important Findings */}
              {summary.summary.important_findings.length > 0 && (
                <div className="p-3.5 rounded-xl bg-surface-container/60 border border-glass-border">
                  <span className="font-label-code text-caption text-text-highlight uppercase block mb-2">
                    Critical Findings
                  </span>
                  <ul className="list-disc list-inside space-y-1 text-text-primary">
                    {summary.summary.important_findings.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Document Preview Iframe Modal */}
      {preview && (
        <div className="fixed inset-0 z-[100] bg-background-canvas/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-5xl h-[85vh] rounded-2xl bg-surface-container-low border border-glass-border backdrop-blur-3xl p-4 shadow-2xl flex flex-col gap-3 overflow-hidden">
            <div className="flex items-center justify-between pb-2 border-b border-glass-border">
              <span className="font-headline-sm text-sm text-primary font-medium truncate">{preview.name}</span>
              <button onClick={closePreview} className="text-outline hover:text-primary">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <iframe title={preview.name} src={preview.url} className="w-full flex-1 rounded-xl bg-surface-container-lowest" />
          </div>
        </div>
      )}
    </div>
  );
}

function processingLabel(report: Report) {
  if (report.processing_status === "completed") return "✓ Ready";
  if (report.processing_status === "failed") return "Processing failed";
  switch (report.processing_stage) {
    case "extracting_text": return "Extracting text…";
    case "generating_embeddings": return "Generating embeddings…";
    case "storing_vectors": return "Saving report index…";
    case "processing": return "Starting processing…";
    default: return "Queued…";
  }
}
