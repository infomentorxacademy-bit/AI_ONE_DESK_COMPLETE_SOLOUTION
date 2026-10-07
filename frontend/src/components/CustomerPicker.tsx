// components/CustomerPicker.tsx : resolves "which customer is this?" when the agent could not tell (e.g. two Asha Raos).
// WHERE THE INFO GOES: the reply to the customer asks for their city or email. When the customer answers, the support
// agent (you) searches here by name or email, compares the CITY the customer gave with the candidates, and clicks
// "Use this customer". The agent then runs again for that customer. Emails shown are masked by the server.
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CustomerMatch } from "../api/types";
import { ErrorBanner } from "./ErrorBanner";

interface Props {
  suggestedQuery: string;                       // e.g. the name found in the ticket ("Asha Rao")
  busy: boolean;
  onPick: (customerId: string) => void;         // implemented by the parent (runs the agent again)
}

export function CustomerPicker({ suggestedQuery, busy, onPick }: Props) {
  const [query, setQuery] = useState(suggestedQuery);
  const [matches, setMatches] = useState<CustomerMatch[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function search(text: string) {
    setError(null);
    try { setMatches(await api.searchCustomers(text.trim())); }
    catch (e) { setError((e as Error).message); }
  }

  // Search straight away when the ticket already names the customer, so the candidates are visible immediately.
  useEffect(() => { if (suggestedQuery.trim().length >= 2) void search(suggestedQuery); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [suggestedQuery]);

  return (
    <div className="picker">
      <p className="hint">
        The customer was asked for their <strong>city or email</strong>. When they reply, find their account here and
        choose the one whose city matches.
      </p>
      <div className="edit">
        <label htmlFor="customer-query">Search by name or exact email</label>
        <input id="customer-query" value={query} onChange={(e) => setQuery(e.target.value)} />
        <button className="btn" disabled={query.trim().length < 2} onClick={() => search(query)}>Search</button>
      </div>
      <ErrorBanner message={error} />
      {matches?.length === 0 && <p className="muted">No customer found. Try another name or the exact email.</p>}
      {matches && matches.length > 0 && (
        <table className="table table--compact" aria-label="Matching customers">
          <thead><tr><th>Id</th><th>Name</th><th>City</th><th>Email</th><th /></tr></thead>
          <tbody>
            {matches.map((m) => (
              <tr key={m.id}>
                <td>{m.id}</td><td>{m.name}</td><td>{m.city}</td><td>{m.email_masked}</td>
                <td><button className="btn btn--primary" disabled={busy} onClick={() => onPick(m.id)}>Use this customer</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
