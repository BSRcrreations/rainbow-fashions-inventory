import { useCallback, useEffect, useRef, useState } from "react";

type StoredFile = { name: string; type: string; modified: number; bytes?: ArrayBuffer; blob?: Blob };
function access<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const open = indexedDB.open("rainbow-draft-attachments", 1);
    open.onupgradeneeded = () => open.result.createObjectStore("files");
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const db = open.result;
      const transaction = db.transaction("files", mode);
      const request = action(transaction.objectStore("files"));
      transaction.oncomplete = () => { db.close(); resolve(request.result); };
      transaction.onabort = transaction.onerror = () => { db.close(); reject(transaction.error); };
    };
  });
}

/** Attachments stay within the same device, store and signed-in user's draft. */
export function useDraftAttachment(key: string, enabled = true) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(enabled);
  const [error, setError] = useState("");
  const version = useRef(0);
  useEffect(() => {
    if (!enabled) return;
    const revision = ++version.current;
    setBusy(true);
    access<StoredFile | undefined>("readonly", store => store.get(key)).then(stored => {
      if (version.current === revision) setFile(stored ? new File([stored.bytes ?? stored.blob ?? new ArrayBuffer(0)], stored.name, { type: stored.type, lastModified: stored.modified }) : null);
    }).catch(() => { if (version.current === revision) setError("Photo recovery is unavailable on this device. Keep the page open until the photo uploads."); })
      .finally(() => { if (version.current === revision) setBusy(false); });
    return () => { if (version.current === revision) version.current = revision + 1; };
  }, [key, enabled]);
  const select = useCallback(async (next: File | null) => {
    const revision = ++version.current;
    setFile(next); setBusy(true); setError("");
    try {
      if (next) {
        // Store bytes rather than browser-managed File handles, which WebKit can
        // discard when the document that selected the file is unloaded.
        const bytes = await new Promise<ArrayBuffer>((resolve, reject) => {
          const reader = new FileReader(); reader.onload = () => resolve(reader.result as ArrayBuffer);
          reader.onerror = () => reject(reader.error); reader.readAsArrayBuffer(next);
        });
        await access("readwrite", store => store.put({ name: next.name, type: next.type, modified: next.lastModified, bytes }, key));
      }
      else await access("readwrite", store => store.delete(key));
    } catch { if (version.current === revision) setError("This photo could not be saved on the device. Keep the page open until it uploads."); }
    finally { if (version.current === revision) setBusy(false); }
  }, [key]);
  return { file, busy, error, select };
}
