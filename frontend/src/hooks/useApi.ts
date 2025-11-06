import { useCallback, useEffect, useState } from "react";
import type { ApiState } from "@lib/types";

// Small wrapper around async data loading so callers get consistent loading/error flags.
export const useApi = <T,>(loader: () => Promise<T>, deps: unknown[] = []): ApiState<T> => {
  const [state, setState] = useState<ApiState<T>>({ data: null, loading: true, error: null });
  // Memoise the fetch routine so we only refire when the caller's dependency list changes.
  const execute = useCallback(async () => {
    try {
      setState({ data: null, loading: true, error: null });
      const data = await loader();
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState({ data: null, loading: false, error: error instanceof Error ? error.message : "Unknown error" });
    }
  }, deps);
  // Kick the fetch whenever the dependencies indicate the underlying request should change.
  useEffect(() => { void execute(); }, [execute]);
  return state;
};
