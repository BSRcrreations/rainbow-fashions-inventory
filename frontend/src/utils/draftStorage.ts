import type { User } from "../types";

export function draftKey(user: Pick<User, "id" | "store_id"> | null, workflow: string) {
  return `rainbow-draft:v1:${user?.store_id ?? "no-store"}:${user?.id ?? "signed-out"}:${workflow}`;
}

export function readDraft<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const saved = JSON.parse(raw) as { version?: number; value?: T };
    return saved.version === 1 && saved.value !== undefined ? saved.value : fallback;
  } catch { return fallback; }
}

export function writeDraft<T>(key: string, value: T): boolean {
  try { localStorage.setItem(key, JSON.stringify({ version: 1, savedAt: new Date().toISOString(), value })); return true; }
  catch { return false; }
}

export function removeDraft(key: string) {
  try { localStorage.removeItem(key); } catch { /* A failed clear must not prevent showing a completed transaction. */ }
}

export type Submission<T> = { key: string; payload: T };

/** An uncertain request is retried with its original payload and key, including after refresh. */
export function prepareSubmission<T>(key: string, payload: T): Submission<T> {
  const previous = readDraft<Submission<T> | null>(key, null);
  if (previous) return previous;
  const next = { key: crypto.randomUUID(), payload };
  if (!writeDraft(key, next)) throw new Error("Your device cannot save this request safely. Free some storage and try again.");
  return next;
}
