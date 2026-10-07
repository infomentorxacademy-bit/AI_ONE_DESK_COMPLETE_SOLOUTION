// components/RunPanel.tsx : shows the result of running the agent on a ticket (or of answering an approval).
// Three possible states:
//   * paused    -> shows the approval card right here so the user can answer immediately
//   * needs_clarification -> shows the customer search (CustomerPicker): pick the right account and the agent runs again
//   * finished  -> shows kind, outcome, final status and the drafted customer reply
import type { ApprovalAnswer, Approver, RunResult } from "../api/types";
import { ApprovalCard } from "./ApprovalCard";
import { CustomerPicker } from "./CustomerPicker";
import { StatusBadge } from "./StatusBadge";

interface Props {
  result: RunResult;
  approver: Approver | undefined;
  busy: boolean;
  onAnswer: (answer: ApprovalAnswer) => void;
  onClarify: (customerId: string) => void;
  ticketText: string;                   // used to pre-fill the customer search with the name in the ticket
}

/** "I am Asha Rao ..." -> "Asha Rao" (empty when the ticket gives no name). */
function nameFromTicket(text: string): string {
  return /\bI(?: am|'m)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)/.exec(text)?.[1] ?? "";
}

export function RunPanel({ result, approver, busy, onAnswer, onClarify, ticketText }: Props) {
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
        <CustomerPicker suggestedQuery={nameFromTicket(ticketText)} busy={busy} onPick={onClarify} />
      )}
    </section>
  );
}
