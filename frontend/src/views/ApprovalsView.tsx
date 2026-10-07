// views/ApprovalsView.tsx : every refund that is waiting for a human. Approve / reject / edit / cancel right here.
// When a card is answered, the agent resumes; if another role is still needed, a fresh card appears.
import { api } from "../api/client";
import type { Approver } from "../api/types";
import { ApprovalCard } from "../components/ApprovalCard";
import { ErrorBanner } from "../components/ErrorBanner";
import { StatusBadge } from "../components/StatusBadge";
import { useAgentActions } from "../hooks/useAgentActions";
import { useAsync } from "../hooks/useAsync";

interface Props { approver: Approver | undefined; refreshKey: number; onChanged: () => void }

export function ApprovalsView({ approver, refreshKey, onChanged }: Props) {
  const { data, error, loading } = useAsync(() => api.approvals(), [refreshKey]);
  const agent = useAgentActions(onChanged);

  return (
    <section className="panel">
      <h2>Waiting for approval</h2>
      <ErrorBanner message={error ?? agent.error} />
      {agent.result?.state === "finished" && (
        <div className="banner banner--ok" role="status">
          {agent.result.ticket_id}: <code>{agent.result.outcome}</code>{" "}
          {agent.result.final_status && <StatusBadge status={agent.result.final_status} />}
        </div>
      )}
      {loading && !data ? <p className="muted">Loading…</p> : data?.length === 0
        ? <p className="muted">Nothing is waiting. Run a refund ticket (for example T3 or T10) from the Tickets tab.</p>
        : <div className="grid">{data?.map((item) => (
            <ApprovalCard key={item.thread_id} card={item.card} approver={approver} busy={agent.busy}
                          onAnswer={(a) => agent.answer(item.thread_id, a)} />
          ))}</div>}
    </section>
  );
}
