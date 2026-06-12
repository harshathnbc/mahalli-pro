"use client";

import { useTranslations } from "next-intl";
import { DataCard, FetchState } from "@/components/DataCard";
import { useApi, asList } from "@/lib/useApi";

interface Vendor {
  id: string;
  name: string;
  vat_number: string;
  classification: string;
  verified_lc_score: string | null;
}

export default function ProcurementPage() {
  const t = useTranslations("nav");
  const { data, loading, error } = useApi("/procurement/vendors/");
  const vendors = asList<Vendor>(data);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("procurement")}</h1>
      <DataCard title="Vendor Directory">
        <FetchState loading={loading} error={error} empty={!loading && !error && vendors.length === 0} />
        {vendors.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-start text-slate-500">
                <th className="py-2 text-start">Name</th>
                <th className="py-2 text-start">VAT</th>
                <th className="py-2 text-start">Type</th>
                <th className="py-2 text-start">LC Score</th>
              </tr>
            </thead>
            <tbody>
              {vendors.map((v) => (
                <tr key={v.id} className="border-t border-slate-100">
                  <td className="py-2">{v.name}</td>
                  <td className="py-2">{v.vat_number}</td>
                  <td className="py-2">
                    <span
                      className={
                        v.classification === "LOCAL" ? "text-brand" : "text-amber-600"
                      }
                    >
                      {v.classification}
                    </span>
                  </td>
                  <td className="py-2">{v.verified_lc_score ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DataCard>
    </div>
  );
}
