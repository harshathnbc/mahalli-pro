"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";

/** Toggles between Arabic (RTL) and English (LTR), preserving the current path. */
export function LangSwitcher() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  const next = locale === "ar" ? "en" : "ar";

  return (
    <button
      type="button"
      onClick={() => router.replace(pathname, { locale: next })}
      className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
    >
      {t("switchLang")}
    </button>
  );
}
