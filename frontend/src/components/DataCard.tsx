"use client";

import type { ReactNode } from "react";

export function DataCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      {children}
    </section>
  );
}

export function FetchState({
  loading,
  error,
  empty,
}: {
  loading: boolean;
  error: string | null;
  empty?: boolean;
}) {
  if (loading) return <p className="text-sm text-slate-400">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (empty) return <p className="text-sm text-slate-400">No data yet.</p>;
  return null;
}
