// components/RunPanel.tsx : shows the result of running the agent on a ticket (or of answering an approval).
// Three possible states:
//   * paused    -> shows the approval card right here so the user can answer immediately
//   * needs_clarification -> offers a small form: "which customer is this? (e.g. C011)" and runs again
//   * finished  -> shows kind, outcome, final status and the drafted customer reply
import { useState } from "react";
import type { ApprovalAnswer, Approver, RunResult } from "../api/types";
import { ApprovalCard } from "./ApprovalCard";
import { StatusBadge } from "./StatusBadge";

interface Props {
  result: RunResult;
  approver: Approver | undefined;
  busy: boolean;
  onAnswer: (answer: ApprovalAnswer) => void;
  onClarify: (customerId: string) => void;
}

export function RunPanel({ result, approver, busy, onAnswer, onClarify }: Props) {
  const [customerId, setCustomerId] = useState("");

  if (result.state === "paused" && result.card) {
    return <ApprovalCard card={result.card} approver={approver} busy={busy} onAnswer={onAnswer} />;
  }
  return (
    <section className="card result" aria-label="Agent result">
      <h3>Agent result</h3>
      <dl className="facts">
        <dt>Kind</dt><dd>{result.kind}</dd>
        <dt>Outcome</dt><dd><code>{result.outcome}</code></dd>
        <dt>Final status</dt><dd>{result.final_status && <StatusBadge status={result.final_status} />}</dd>
        {result.flags.length > 0 && <><dt>Flags</dt><dd>{result.flags.map((f) => <span key={f} className="flag">{f}</span>)}</dd></>}
      </dl>
      {result.reply && <blockquote className="reply">{result.reply}</blockquote>}
      {result.outcome === "needs_clarification" && (
        <div className="edit">
          <label htmlFor="clarify">Which customer is this? (customer id, e.g. C011)</label>
          <input id="clarify" value={customerId} onChange={(e) => setCustomerId(e.target.value.trim().toUpperCase())} />
          <button className="btn" disabled={busy || !/^C\d{3}$/.test(customerId)} onClick={() => onClarify(customerId)}>
            Run again with this customer
          </button>
        </div>
      )}
    </section>
  );
}
