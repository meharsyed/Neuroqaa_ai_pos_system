import { apiClient } from "./axios";
import { toast } from "./use-toast";

/**
 * Open a PDF the API generates.
 *
 * It has to go through `apiClient`, not a plain <a href>. The access token
 * lives in memory and is attached by an axios interceptor — a browser
 * navigation to /api/... carries no Authorization header, so the API answers
 * 401 and the user gets DRF's browsable-API error page instead of their
 * document. That is exactly what happened to the quotation Print button.
 */
export async function openApiPdf(
  url: string,
  { params, failure = "Could not open the document" }: {
    params?: Record<string, unknown>;
    failure?: string;
  } = {}
): Promise<void> {
  try {
    const response = await apiClient.get<Blob>(url, { params, responseType: "blob" });
    const blobUrl = URL.createObjectURL(response.data);
    const win = window.open(blobUrl, "_blank", "noopener");
    if (!win) {
      toast({
        title: "Popup blocked",
        description: "Allow popups for this site to view the document.",
        variant: "error",
      });
      URL.revokeObjectURL(blobUrl);
      return;
    }
    // The new tab needs the URL to still resolve while it loads; revoking
    // immediately gives a blank tab in some browsers.
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  } catch (err) {
    toast({ title: failure, description: await blobErrorMessage(err), variant: "error" });
  }
}

/**
 * Read a Blob as text.
 *
 * `Blob.prototype.text()` is the obvious way and works in every browser this
 * runs in — but not in jsdom, so a test covering the error path could only
 * ever assert the fallback. FileReader works in both, and in the handful of
 * older browsers that predate .text() as well.
 */
function readBlobText(blob: Blob): Promise<string> {
  if (typeof blob.text === "function") return blob.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

/**
 * Pull a readable message out of a failed blob request.
 *
 * With `responseType: "blob"` the error body is a Blob, so the usual
 * `err.response.data.detail` is undefined and the user sees "Request failed
 * with status code 401". The body has to be read back as text first.
 */
export async function blobErrorMessage(err: unknown, fallback = "Please try again."): Promise<string> {
  const response = (err as { response?: { status?: number; data?: unknown } })?.response;
  if (!response) return (err as Error)?.message || fallback;

  if (response.status === 401) {
    return "Your session has expired. Sign in again and retry.";
  }
  if (response.status === 403) {
    return "Your role does not have access to this.";
  }

  const data = response.data;
  if (data instanceof Blob) {
    try {
      const parsed = JSON.parse(await readBlobText(data)) as { detail?: string };
      if (parsed?.detail) return parsed.detail;
    } catch {
      // Not JSON — an HTML error page, most likely. Nothing useful to show.
    }
  } else if (data && typeof data === "object" && "detail" in data) {
    return String((data as { detail: unknown }).detail);
  }
  return fallback;
}
