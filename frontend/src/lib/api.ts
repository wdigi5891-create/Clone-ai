// Chaîne vide = même origine (déploiement tout-en-un : Next relaie /api vers le backend).
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "avc_token";

export class ApiError extends Error {
  constructor(message: string, public status: number, public data: Record<string, unknown> = {}) {
    super(message);
  }
}

export const getToken = () => (typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY));
export const setToken = (t: string | null) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

function toError(status: number, data: any): ApiError {
  let message = data?.message;
  if (!message && Array.isArray(data?.detail)) {
    message = "Données invalides : " + data.detail.map((d: any) => d.msg).join(" ; ");
  }
  if (status === 401 && typeof window !== "undefined" && !location.pathname.startsWith("/login")) {
    setToken(null);
    window.dispatchEvent(new Event("avc-logout"));
  }
  return new ApiError(message || `Erreur du serveur (${status}).`, status, data || {});
}

export async function api<T = unknown>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: options.method || (options.body !== undefined ? "POST" : "GET"),
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError("Serveur injoignable. Vérifiez votre connexion ou que l'API est démarrée.", 0);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw toError(res.status, data);
  return data as T;
}

/** Envoi de fichier avec progression réelle (octets transmis). */
export function uploadVideo<T>(file: File, fields: Record<string, string>, onProgress: (ratio: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    Object.entries(fields).forEach(([k, v]) => form.append(k, v));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/projects/upload`);
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onerror = () => reject(new ApiError("Envoi interrompu : serveur injoignable.", 0));
    xhr.onload = () => {
      let data: any = null;
      try { data = JSON.parse(xhr.responseText); } catch { /* réponse non JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as T);
      else reject(toError(xhr.status, data));
    };
    xhr.send(form);
  });
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/** Téléchargement authentifié d'un export. */
export async function downloadExport(projectId: string, kind: string) {
  const res = await fetch(`${API_URL}/api/projects/${projectId}/export/${kind}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw toError(res.status, await res.json().catch(() => null));
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "")?.[1] || kind;
  saveBlob(await res.blob(), name);
}

/** Téléchargement d'une image via son URL signée. */
export async function downloadUrl(url: string, filename: string) {
  const res = await fetch(url);
  if (!res.ok) throw new ApiError("Téléchargement impossible (lien expiré ?). Rechargez la page.", res.status);
  saveBlob(await res.blob(), filename);
}
