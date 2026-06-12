"use client";

import { useTranslations } from "next-intl";
import { DataCard, FetchState } from "@/components/DataCard";
import { useApi, asList } from "@/lib/useApi";

interface Report {
  id: string;
  level: string;
  type: string;
  state: string;
  computed_score: { total?: string } | null;
}

export default function ReportsPage() {
  const t = useTranslations("nav");
  const { data, loading, error } = useApi("/reports/lc-reports/");
  const reports = asList<Report>(data);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("reports")}</h1>
      <DataCard title="LC Reports & Exports">
        <FetchState loading={loading} error={error} empty={!loading && !error && reports.length === 0} />
        {reports.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500">
                <th className="py-2 text-start">Level</th>
                <th className="py-2 text-start">Type</th>
                <th className="py-2 text-start">State</th>
                <th className="py-2 text-start">Total LC (SAR)</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className="border-t border-slate-100">
                  <td className="py-2">{r.level}</td>
                  <td className="py-2">{r.type}</td>
                  <td className="py-2">{r.state}</td>
                  <td className="py-2">{r.computed_score?.total ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DataCard>
    </div>
  );
}
