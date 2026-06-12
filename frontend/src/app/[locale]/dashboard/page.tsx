"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useAuth } from "@/lib/auth";
import { navForRole } from "@/lib/nav";

export default function DashboardHome() {
  const t = useTranslations();
  const { user } = useAuth();
  if (!user) return null;

  const cards = navForRole(user.role).filter((i) => i.href !== "/dashboard");

  return (
    <div>
      <h1 className="text-2xl font-bold">{t("nav.overview")}</h1>
      <p className="mt-1 text-slate-500">{t("dashboard.welcome")}</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand"
          >
            <div className="text-lg font-semibold">{t(`nav.${c.labelKey}`)}</div>
            <div className="mt-1 text-sm text-slate-500">{t(`dashboard.go`)}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
