import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { LangSwitcher } from "@/components/LangSwitcher";

export default function Landing() {
  const t = useTranslations();
  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <header className="flex items-center justify-between">
        <span className="text-xl font-bold text-brand">{t("brand")}</span>
        <nav className="flex items-center gap-4">
          <LangSwitcher />
          <Link href="/login" className="rounded-md bg-brand px-4 py-2 text-white">
            {t("nav.login")}
          </Link>
        </nav>
      </header>

      <section className="mt-20">
        <h1 className="text-4xl font-extrabold leading-tight">{t("landing.heading")}</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-600">{t("landing.subheading")}</p>
        <Link
          href="/login"
          className="mt-8 inline-block rounded-lg bg-brand px-6 py-3 font-semibold text-white hover:bg-brand-dark"
        >
          {t("landing.cta")}
        </Link>
      </section>
    </main>
  );
}
