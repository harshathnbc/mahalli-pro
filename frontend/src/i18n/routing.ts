import { defineRouting } from "next-intl/routing";

// Arabic (RTL) is the default; English (LTR) is the secondary locale.
export const routing = defineRouting({
  locales: ["ar", "en"],
  defaultLocale: "ar",
});

export type Locale = (typeof routing.locales)[number];

export const localeDir: Record<Locale, "rtl" | "ltr"> = {
  ar: "rtl",
  en: "ltr",
};
