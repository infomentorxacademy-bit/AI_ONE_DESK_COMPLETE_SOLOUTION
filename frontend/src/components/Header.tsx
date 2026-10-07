// components/Header.tsx : the top bar: product name, LLM chooser, "acting as" approver menu, reset button.
// "Acting as" is who the system records as the approver when you click Approve. This demo has NO login,
// so the menu is clearly labelled; a real deployment must authenticate users and take the identity from the login.
import { api } from "../api/client";
import type { AppConfig, Approver } from "../api/types";
import { LlmSelector } from "./LlmSelector";

interface Props {
  config: AppConfig;
  approvers: Approver[];
  actingAs: string;
  onActingAs: (id: string) => void;
  onConfigChanged: () => void;
  onDataReset: () => void;
}

export function Header({ config, approvers, actingAs, onActingAs, onConfigChanged, onDataReset }: Props) {
  async function reset() {
    if (!window.confirm("Reset ALL demo data to the original TechNova dataset?")) return;
    await api.reset();
    onDataReset();
  }

  return (
    <header className="header">
      <div className="brand">
        <strong>OpsDesk</strong> <span className="muted">TechNova Retail · customer support agent</span>
      </div>
      <div className="header__controls">
        <LlmSelector config={config} onChanged={onConfigChanged} />
        <div className="acting">
          <label htmlFor="acting-as">Acting as (demo, no login)</label>
          <select id="acting-as" value={actingAs} onChange={(e) => onActingAs(e.target.value)}>
            {approvers.map((a) => <option key={a.id} value={a.id}>{a.name} · {a.id} · {a.role.replace("_", " ")}</option>)}
          </select>
        </div>
        {config.reset_enabled && <button className="btn btn--ghost" onClick={reset}>Reset demo data</button>}
      </div>
    </header>
  );
}
