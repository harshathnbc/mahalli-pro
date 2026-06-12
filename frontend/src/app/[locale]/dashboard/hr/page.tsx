"use client";

import { useTranslations } from "next-intl";
import { DataCard, FetchState } from "@/components/DataCard";
import { useApi, asList } from "@/lib/useApi";

interface Upload {
  id: string;
  month: number;
  status: string;
}

export default function HrPage() {
  const t = useTranslations("nav");
  const { data, loading, error } = useApi("/hr/uploads/");
  const uploads = asList<Upload>(data);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("hr")}</h1>
      <DataCard title="Monthly Payroll Uploads (12 slots)">
        <FetchState loading={loading} error={error} empty={!loading && !error && uploads.length === 0} />
        {uploads.length > 0 && (
          <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {uploads.map((u) => (
              <li key={u.id} className="rounded border border-slate-200 p-3 text-sm">
                <div className="font-semibold">Month {u.month}</div>
                <div className="text-slate-500">{u.status}</div>
              </li>
            ))}
          </ul>
        )}
      </DataCard>
    </div>
  );
}
