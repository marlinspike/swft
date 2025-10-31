import { useCallback, useEffect, useState } from "react";
import type { ApiState } from "@lib/types";

export const useApi = <T,>(loader: () => Promise<T>, deps: unknown[] = []): ApiState<T> => {
  const [state, setState] = useState<ApiState<T>>({ data: null, loading: true, error: null });
  const execute = useCallback(async () => {
    try {
      setState({ data: null, loading: true, error: null });
      const data = await loader();
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState({ data: null, loading: false, error: error instanceof Error ? error.message : "Unknown error" });
    }
  }, deps);
  useEffect(() => { void execute(); }, [execute]);
  return state;
};
