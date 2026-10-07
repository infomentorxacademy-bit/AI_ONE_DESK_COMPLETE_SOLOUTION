// components/LlmSelector.tsx : "Which LLM to use?" - choose OpenAI or Groq (the product has no fake model).
// It shows which providers have an API key configured on the SERVER. Keys are never typed in the browser:
// they live in app/.env on the server, so they can never leak through the UI.
import { useState } from "react";
import { api } from "../api/client";
import type { AppConfig } from "../api/types";
import { ErrorBanner } from "./ErrorBanner";

interface Props { config: AppConfig; onChanged: () => void }

export function LlmSelector({ config, onChanged }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function choose(provider: string) {
    setBusy(true);
    setError(null);
    try {
      await api.selectLlm(provider);       // backend rebuilds the agent around the chosen model
      onChanged();                          // tell App to reload the config
    } catch (e) {
      setError((e as Error).message);       // e.g. "GROQ_API_KEY is not set..."
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="llm">
      <label htmlFor="llm-select">LLM</label>
      <select id="llm-select" disabled={busy} value={config.llm?.split(":")[0] ?? ""}
              onChange={(e) => choose(e.target.value)}>
        <option value="" disabled>Choose…</option>
        {config.providers.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name === "openai" ? "OpenAI" : "Groq"} · {p.model}{p.configured ? "" : " (no key)"}
          </option>
        ))}
      </select>
      <ErrorBanner message={error} />
    </div>
  );
}
