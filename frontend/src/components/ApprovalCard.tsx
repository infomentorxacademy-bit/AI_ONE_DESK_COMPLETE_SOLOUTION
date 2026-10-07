// components/ApprovalCard.tsx : the card a support lead / finance approver sees when the agent pauses.
// Facts first, recommendation last (requirement NFR-17: readable in 15 seconds).
// It does NOT decide anything: it only builds the answer object and hands it to `onAnswer`.
import { useState } from "react";
import type { ApprovalAnswer, ApprovalCardData, Approver } from "../api/types";

interface Props {
  card: ApprovalCardData;
  approver: Approver | undefined;               // who is "acting as" (from the header menu)
  busy: boolean;
  onAnswer: (answer: ApprovalAnswer) => void;   // implemented by the parent view (calls the API)
}

export function ApprovalCard({ card, approver, busy, onAnswer }: Props) {
  const [newAmount, setNewAmount] = useState(String(card.amount));

  // The acting person can only approve if their role is one of the roles this card still needs.
  const canApprove = !!approver && card.needs.includes(approver.role);
  const who = approver ? { approver_id: approver.id, role: approver.role } : {};
  const amountNumber = Number(newAmount);
  const amountOk = Number.isInteger(amountNumber) && amountNumber > 0;

  return (
    <article className="card approval" aria-label={`Approval for ${card.ticket_id}`}>
      <h3>Refund approval · {card.ticket_id}</h3>
      <dl className="facts">
        <dt>Order</dt><dd>{card.order_id} · {card.item}</dd>
        <dt>Amount</dt><dd>Rs {card.amount.toLocaleString("en-IN")}</dd>
        <dt>Still needs</dt><dd>{card.needs.map((r) => r.replace("_", " ")).join(" + ")}</dd>
        <dt>Rule</dt><dd><code>{card.rule}</code></dd>
        {card.flags.length > 0 && <><dt>Flags (internal)</dt><dd>{card.flags.map((f) => <span key={f} className="flag">{f}</span>)}</dd></>}
      </dl>
      <p className="recommendation">{card.recommendation}</p>

      {!canApprove && approver && (
        <p className="hint">This step needs {card.needs.join(" or ")}. Switch “Acting as” (top right) to approve.</p>
      )}

      <div className="actions">
        <button className="btn btn--primary" disabled={busy || !canApprove}
                onClick={() => onAnswer({ action: "approve", ...who })}>Approve</button>
        <button className="btn btn--danger" disabled={busy || !approver}
                onClick={() => onAnswer({ action: "reject", ...who })}>Reject</button>
        <button className="btn btn--ghost" disabled={busy}
                onClick={() => onAnswer({ action: "cancel" })}>Cancel (decide later)</button>
      </div>

      <div className="edit">
        <label htmlFor={`amt-${card.ticket_id}`}>Approve a different amount</label>
        <input id={`amt-${card.ticket_id}`} inputMode="numeric" value={newAmount}
               onChange={(e) => setNewAmount(e.target.value)} />
        <button className="btn" disabled={busy || !canApprove || !amountOk}
                onClick={() => onAnswer({ action: "edit_amount", amount: amountNumber, ...who })}>Edit &amp; approve</button>
      </div>
    </article>
  );
}
