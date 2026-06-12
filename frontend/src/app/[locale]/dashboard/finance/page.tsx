"use client";

import { useTranslations } from "next-intl";
import { DataCard, FetchState } from "@/components/DataCard";
import { useApi, asList } from "@/lib/useApi";

interface Reconciliation {
  id: string;
  scope: string;
  variance_pct: string | null;
  passed: boolean;
}

export default function FinancePage() {
  const t = useTranslations("nav");
  const { data, loading, error } = useApi("/finance/reconciliations/");
  const checks = asList<Reconciliation>(data);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("finance")}</h1>
      <DataCard title="Reconciliation (±5% Strict Block)">
        <FetchState loading={loading} error={error} empty={!loading && !error && checks.length === 0} />
        {checks.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500">
                <th className="py-2 text-start">Scope</th>
                <th className="py-2 text-start">Variance</th>
                <th className="py-2 text-start">Result</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((c) => (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="py-2">{c.scope}</td>
                  <td className="py-2">
                    {c.variance_pct ? `${(Number(c.variance_pct) * 100).toFixed(2)}%` : "—"}
                  </td>
                  <td className="py-2">
                    <span className={c.passed ? "text-brand" : "text-red-600"}>
                      {c.passed ? "● Pass" : "● Red Light"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DataCard>
    </div>
  );
}
