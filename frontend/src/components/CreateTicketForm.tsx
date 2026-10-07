// components/CreateTicketForm.tsx : a small form to add a new support ticket (status "new").
import { useState } from "react";
import { api } from "../api/client";
import type { Ticket } from "../api/types";
import { ErrorBanner } from "./ErrorBanner";

interface Props { onCreated: (ticket: Ticket) => void }

export function CreateTicketForm({ onCreated }: Props) {
  const [text, setText] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();                       // stop the browser from reloading the page
    setBusy(true);
    setError(null);
    try {
      const ticket = await api.createTicket(text.trim(), customerId.trim().toUpperCase() || undefined);
      setText("");
      setCustomerId("");
      onCreated(ticket);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h3>New ticket</h3>
      <label htmlFor="ticket-text">What does the customer say?</label>
      <textarea id="ticket-text" rows={3} value={text} onChange={(e) => setText(e.target.value)}
                placeholder="e.g. Where is my order O1003?" />
      <label htmlFor="ticket-customer">Customer id (optional)</label>
      <input id="ticket-customer" value={customerId} onChange={(e) => setCustomerId(e.target.value)} placeholder="C004" />
      <ErrorBanner message={error} />
      <button className="btn btn--primary" disabled={busy || text.trim().length < 3}>Create ticket</button>
    </form>
  );
}
