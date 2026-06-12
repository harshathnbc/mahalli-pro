"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { DataCard } from "@/components/DataCard";
import { apiFetch } from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

export default function CopilotPage() {
  const t = useTranslations("nav");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [conversation, setConversation] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    const query = input;
    setMessages((m) => [...m, { role: "user", content: query }]);
    setInput("");
    setBusy(true);
    try {
      const res = await apiFetch<{
        conversation: string;
        message: { content: string };
      }>("/copilot/ask/", {
        method: "POST",
        body: JSON.stringify({ query, conversation: conversation ?? undefined }),
      });
      setConversation(res.conversation);
      setMessages((m) => [...m, { role: "assistant", content: res.message.content }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `⚠️ ${String(err)}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("copilot")}</h1>
      <DataCard title="Compliance Copilot (grounded, RBAC-scoped)">
        <div className="mb-4 max-h-96 space-y-3 overflow-y-auto">
          {messages.length === 0 && (
            <p className="text-sm text-slate-400">
              Ask about LCGPA or ZATCA rules. Answers are grounded in documents your role
              is authorized to see.
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`rounded-lg px-3 py-2 text-sm ${
                m.role === "user" ? "bg-brand text-white" : "bg-slate-100 text-slate-800"
              }`}
            >
              {m.content}
            </div>
          ))}
        </div>
        <form onSubmit={ask} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
            placeholder="Ask a question…"
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "…" : "Send"}
          </button>
        </form>
      </DataCard>
    </div>
  );
}
