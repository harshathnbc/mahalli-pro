"use client";

import { useEffect, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { LangSwitcher } from "@/components/LangSwitcher";
import { useAuth } from "@/lib/auth";
import { navForRole } from "@/lib/nav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const t = useTranslations();
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return <div className="flex min-h-screen items-center justify-center text-slate-400">…</div>;
  }

  const items = navForRole(user.role);

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-e border-slate-200 bg-slate-50 p-4">
        <div className="mb-6 text-lg font-bold text-brand">{t("brand")}</div>
        <nav className="space-y-1">
          {items.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded-md px-3 py-2 text-sm ${
                  active ? "bg-brand text-white" : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {t(`nav.${item.labelKey}`)}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 px-6 py-3">
          <span className="text-sm text-slate-500">{t(`roles.${user.role}`)}</span>
          <div className="flex items-center gap-3">
            <LangSwitcher />
            <button
              onClick={() => {
                signOut();
                router.replace("/login");
              }}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
            >
              {t("nav.logout")}
            </button>
          </div>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
