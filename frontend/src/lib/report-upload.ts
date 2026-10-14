export type Report = {
  id: string;
  session_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  processing_status: "pending" | "processing" | "completed" | "failed";
  processing_stage: "queued" | "extracting_text" | "generating_embeddings" | "ready" | "failed";
  upload_date: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const ACCEPTED_REPORTS = ".pdf,.png,.jpg,.jpeg,.webp";
export const MAX_REPORT_SIZE = 20 * 1024 * 1024;

export function uploadReport(
  file: File,
  sessionId: string,
  token: string,
  onProgress: (value: number) => void,
  timeoutMs = 120_000,
): Promise<Report> {
  return new Promise((resolve, reject) => {
    const body = new FormData();
    body.append("file", file);
    const url = `${API_BASE}/reports/upload?session_id=${encodeURIComponent(sessionId)}`;
    const request = new XMLHttpRequest();
    request.open("POST", url);
    request.timeout = timeoutMs;
    request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.upload.onprogress = event => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("Network error while uploading. Check your connection and retry."));
    request.ontimeout = () => reject(new Error("Upload timed out after 2 minutes. Retry when your connection is stable."));
    request.onabort = () => reject(new Error("Upload was cancelled."));
    request.onload = () => {
      if (request.status < 200 || request.status >= 300) {
        try {
          const body: unknown = JSON.parse(request.responseText);
          const detail = typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string" ? body.detail : "Upload failed. Please retry.";
          reject(new Error(detail));
        } catch {
          reject(new Error("Upload failed. Please retry."));
        }
        return;
      }
      try {
        resolve(JSON.parse(request.responseText) as Report);
      } catch {
        reject(new Error("The server returned an invalid upload response."));
      }
    };
    request.send(body);
  });
}
