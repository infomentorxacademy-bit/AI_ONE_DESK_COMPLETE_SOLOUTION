// src/hooks/useAsync.ts : a tiny hook for "load some data, show loading / error, let me reload".
// A hook is a reusable piece of component logic. This one removes the same loading/error code from every view.
import { useCallback, useEffect, useState } from "react";

export interface AsyncState<T> { data: T | undefined; error: string | null; loading: boolean; reload: () => void }

/**
 * Run `load()` when the component appears and whenever any value in `deps` changes.
 * `reload()` runs it again on demand (for example after the user approves something).
 */
export function useAsync<T>(load: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;            // ignore the answer if the component changed its mind meanwhile
    setLoading(true);
    load()
      .then((result) => { if (!cancelled) { setData(result); setError(null); } })
      .catch((e: Error) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { data, error, loading, reload };
}
