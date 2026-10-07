// views/TicketsView.tsx : the main screen: filter + queue on the left, the selected ticket (or a new-ticket form) on the right.
import { useState } from "react";
import { api } from "../api/client";
import type { Approver } from "../api/types";
import { CreateTicketForm } from "../components/CreateTicketForm";
import { ErrorBanner } from "../components/ErrorBanner";
import { TicketDetail } from "../components/TicketDetail";
import { TicketList } from "../components/TicketList";
import { useAsync } from "../hooks/useAsync";

const FILTERS = ["", "new", "in_progress", "pending_approval", "resolved", "declined", "escalated", "linked_to_incident"];

interface Props { approver: Approver | undefined; llmReady: boolean; refreshKey: number; onChanged: () => void }

export function TicketsView({ approver, llmReady, refreshKey, onChanged }: Props) {
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const { data, error, loading } = useAsync(() => api.tickets(status || undefined), [status, refreshKey]);

  return (
    <div className="split">
      <section className="panel">
        <div className="toolbar">
          <label htmlFor="status-filter">Status</label>
          <select id="status-filter" value={status} onChange={(e) => setStatus(e.target.value)}>
            {FILTERS.map((f) => <option key={f} value={f}>{f ? f.replaceAll("_", " ") : "all"}</option>)}
          </select>
          <span className="muted">{data ? `${data.length} tickets` : ""}</span>
        </div>
        <ErrorBanner message={error} />
        {loading && !data ? <p className="muted">Loading…</p> : <TicketList tickets={data ?? []} selectedId={selected} onSelect={setSelected} />}
      </section>
      <section className="panel">
        {selected
          ? <TicketDetail ticketId={selected} approver={approver} llmReady={llmReady} refreshKey={refreshKey} onChanged={onChanged} />
          : <p className="muted">Select a ticket to see it, or create a new one below.</p>}
        <CreateTicketForm onCreated={(t) => { setSelected(t.id); onChanged(); }} />
      </section>
    </div>
  );
}
