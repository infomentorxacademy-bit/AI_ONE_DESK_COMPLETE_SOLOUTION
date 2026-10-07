// views/IncidentsView.tsx : the outage detector. Press the button to run Graph B: it looks for 3+ similar payment-failure
// tickets, matches the error spike to a deployment, links the tickets to the incident and PROPOSES (never executes) a rollback.
import { useState } from "react";
import { api } from "../api/client";
import type { IncidentRun } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { useAsync } from "../hooks/useAsync";

interface Props { llmReady: boolean; refreshKey: number; onChanged: () => void }

export function IncidentsView({ llmReady, refreshKey, onChanged }: Props) {
  const incidents = useAsync(() => api.incidents(), [refreshKey]);
  const rollbacks = useAsync(() => api.rollbacks(), [refreshKey]);
  const [run, setRun] = useState<IncidentRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function detect() {
    setBusy(true);
    setError(null);
    try { setRun(await api.runIncident()); onChanged(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <div className="stack">
      <section className="panel">
        <div className="toolbar">
          <h2>Outage detection</h2>
          <button className="btn btn--primary" disabled={busy || !llmReady} onClick={detect}>
            {busy ? "Analysing…" : "Run outage detection"}
          </button>
          {!llmReady && <span className="hint">Choose an LLM (top bar) first.</span>}
        </div>
        <ErrorBanner message={error} />
        {run && run.cluster_ids.length === 0 && <p className="muted">No outage found in the new tickets.</p>}
        {run && run.cluster_ids.length > 0 && (
          <div className="card">
            <dl className="facts">
              <dt>Cluster</dt><dd>{run.cluster_ids.length} tickets ({run.cluster_ids[0]} … {run.cluster_ids.at(-1)})</dd>
              <dt>Error spike</dt><dd>{run.spike?.baseline}% → {run.spike?.value}% at {run.spike?.first_time}</dd>
              <dt>Suspect deployment</dt>
              <dd>{run.correlated ? `${run.correlated.id} ${run.correlated.version} (${run.correlated.minutes_before_spike} min before the spike)` : "none found"}</dd>
              <dt>Incident</dt><dd>{run.incident_id ?? "none open"}</dd>
              <dt>Rollback</dt><dd>{run.proposal ? `${run.proposal.id} · ${run.proposal.status} (NOT executed)` : "not proposed"}</dd>
              {run.flags?.length ? <><dt>Flags</dt><dd>{run.flags.map((f) => <span key={f} className="flag">{f}</span>)}</dd></> : null}
            </dl>
            <h3>Engineer note</h3><pre className="note">{run.engineer_note}</pre>
            <h3>Customer message</h3><blockquote className="reply">{run.customer_message}</blockquote>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Incidents</h2>
        <ErrorBanner message={incidents.error} />
        <table className="table">
          <thead><tr><th>Id</th><th>Service</th><th>Severity</th><th>Status</th><th>Tickets</th><th>Title</th></tr></thead>
          <tbody>{incidents.data?.map((i) => (
            <tr key={i.id}><td>{i.id}</td><td>{i.service}</td><td>{i.severity}</td><td>{i.status}</td><td>{i.ticket_count}</td><td className="clip">{i.title}</td></tr>
          ))}</tbody>
        </table>
        <h2>Rollback proposals</h2>
        <p className="muted">Proposals only. A human must approve and execute any rollback outside this system.</p>
        {rollbacks.data?.length === 0 ? <p className="muted">None yet.</p> : (
          <table className="table"><thead><tr><th>Id</th><th>Deployment</th><th>Status</th><th>Evidence</th></tr></thead>
            <tbody>{rollbacks.data?.map((r) => <tr key={r.id}><td>{r.id}</td><td>{r.deployment_id}</td><td>{r.status}</td><td className="clip">{r.evidence}</td></tr>)}</tbody></table>
        )}
      </section>
    </div>
  );
}
