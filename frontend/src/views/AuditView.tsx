// views/AuditView.tsx : the audit log: every status change, refund issued/blocked, link and rollback proposal.
// This is how "who approved which refund" can be shown on demand (requirement NFR-18).
import { useState } from "react";
import { api } from "../api/client";
import { AuditTable } from "../components/AuditTable";
import { ErrorBanner } from "../components/ErrorBanner";
import { useAsync } from "../hooks/useAsync";

export function AuditView({ refreshKey }: { refreshKey: number }) {
  const [ticketId, setTicketId] = useState("");
  const { data, error, loading } = useAsync(() => api.audit(ticketId.trim() || undefined), [ticketId, refreshKey]);
  return (
    <section className="panel">
      <div className="toolbar">
        <h2>Audit log</h2>
        <label htmlFor="audit-ticket">Ticket</label>
        <input id="audit-ticket" placeholder="all tickets (e.g. T10)" value={ticketId}
               onChange={(e) => setTicketId(e.target.value.toUpperCase())} />
      </div>
      <ErrorBanner message={error} />
      {loading && !data ? <p className="muted">Loading…</p> : <AuditTable entries={data ?? []} />}
    </section>
  );
}
