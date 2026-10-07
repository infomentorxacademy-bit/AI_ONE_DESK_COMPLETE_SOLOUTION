// hooks/useAgentActions.ts : "run the agent on a ticket" and "answer an approval card", with busy/error handling.
// Shared by TicketDetail and ApprovalsView so the same logic is not written twice.
import { useState } from "react";
import { api } from "../api/client";
import type { ApprovalAnswer, RunResult } from "../api/types";

export function useAgentActions(onChanged: () => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);

  /** Wrap any API call: show busy, catch errors, store the result, tell the app something changed. */
  async function perform(action: () => Promise<RunResult>) {
    setBusy(true);
    setError(null);
    try {
      setResult(await action());
      onChanged();                           // refresh tickets / approvals / badge counts
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return {
    busy, error, result,
    clear: () => { setResult(null); setError(null); },
    runTicket: (ticketId: string, customerId?: string) => perform(() => api.runTicket(ticketId, customerId)),
    answer: (threadId: string, answer: ApprovalAnswer) => perform(() => api.answerApproval(threadId, answer)),
  };
}
