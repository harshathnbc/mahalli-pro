import { useTranslations } from "next-intl";

export default function LoginPage() {
  const t = useTranslations("login");
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <form className="mt-6 space-y-4">
        <label className="block">
          <span className="text-sm font-medium">{t("email")}</span>
          <input
            type="email"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            autoComplete="email"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">{t("password")}</span>
          <input
            type="password"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            autoComplete="current-password"
          />
        </label>
        <button
          type="submit"
          className="w-full rounded-md bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark"
        >
          {t("submit")}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-500">{t("hint")}</p>
    </main>
  );
}
