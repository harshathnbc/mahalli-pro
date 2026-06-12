"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "./api";

interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Fetch JSON from the API on mount, with loading/error state. DRF lists may be
 *  paginated ({results: []}) or plain arrays. */
export function useApi<T = unknown>(path: string): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    let active = true;
    apiFetch<T>(path)
      .then((data) => active && setState({ data, error: null, loading: false }))
      .catch((e) => active && setState({ data: null, error: String(e), loading: false }));
    return () => {
      active = false;
    };
  }, [path]);

  return state;
}

export function asList<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[];
  if (data && typeof data === "object" && "results" in data) {
    return (data as { results: T[] }).results;
  }
  return [];
}
