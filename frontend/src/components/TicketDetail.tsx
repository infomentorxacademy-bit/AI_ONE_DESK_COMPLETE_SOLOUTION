// components/TicketDetail.tsx : one ticket in detail: text, status, "Run agent" button, the agent's result and the
// ticket's audit trail. If the agent pauses for approval, the approval card appears right here.
import { useEffect } from "react";
import { api } from "../api/client";
import type { Approver } from "../api/types";
import { useAgentActions } from "../hooks/useAgentActions";
import { useAsync } from "../hooks/useAsync";
import { AuditTable } from "./AuditTable";
import { ErrorBanner } from "./ErrorBanner";
import { RunPanel } from "./RunPanel";
import { StatusBadge } from "./StatusBadge";

interface Props {
  ticketId: string;
  approver: Approver | undefined;
  llmReady: boolean;                 // false until an LLM is chosen (running needs it)
  refreshKey: number;                // changes whenever data changed elsewhere
  onChanged: () => void;
}

export function TicketDetail({ ticketId, approver, llmReady, refreshKey, onChanged }: Props) {
  const { data, error, loading } = useAsync(() => api.ticket(ticketId), [ticketId, refreshKey]);
  const agent = useAgentActions(onChanged);

  // Switching to another ticket clears the previous agent result.
  useEffect(() => { agent.clear(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [ticketId]);

  if (loading && !data) return <p className="muted">Loading…</p>;
  if (!data) return <ErrorBanner message={error} />;
  const { ticket, audit } = data;

  return (
    <section className="detail" aria-label={`Ticket ${ticket.id}`}>
      <div className="detail__head">
        <h2>{ticket.id}</h2>
        <StatusBadge status={ticket.status} />
        {ticket.incident_id && <span className="flag">{ticket.incident_id}</span>}
      </div>
      <p className="ticket-text">{ticket.text}</p>
      <p className="muted">Customer: {ticket.customer_id ?? "unknown"} · created {ticket.created_at.slice(0, 16)}</p>
      {ticket.resolution && <blockquote className="reply">{ticket.resolution}</blockquote>}

      <div className="actions">
        <button className="btn btn--primary" disabled={agent.busy || !llmReady}
                onClick={() => agent.runTicket(ticket.id)}>{agent.busy ? "Running…" : "Run agent on this ticket"}</button>
        {!llmReady && <span className="hint">Choose an LLM (top bar) first.</span>}
      </div>
      <ErrorBanner message={agent.error} />
      {agent.result && (
        <RunPanel result={agent.result} approver={approver} busy={agent.busy}
                  onAnswer={(a) => agent.answer(agent.result!.thread_id, a)}
                  onClarify={(customerId) => agent.runTicket(ticket.id, customerId)} />
      )}

      <h3>History</h3>
      <AuditTable entries={audit} />
    </section>
  );
}
