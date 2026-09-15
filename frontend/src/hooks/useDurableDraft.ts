import { Dispatch, SetStateAction, useCallback, useState } from "react";
import { readDraft, removeDraft, writeDraft } from "../utils/draftStorage";

export function useDurableDraft<T>(key: string, initial: T) {
  const [value, updateValue] = useState<T>(() => readDraft(key, initial));
  const [saved, setSaved] = useState(true);
  const setValue: Dispatch<SetStateAction<T>> = useCallback((next) => {
    updateValue((current) => {
      const updated = typeof next === "function" ? (next as (current: T) => T)(current) : next;
      setSaved(writeDraft(key, updated));
      return updated;
    });
  }, [key]);
  const clear = useCallback(() => { removeDraft(key); updateValue(initial); setSaved(true); }, [initial, key]);
  return { value, setValue, saved, clear };
}
