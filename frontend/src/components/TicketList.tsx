// components/TicketList.tsx : the queue as a table. Clicking a row selects that ticket (shown in TicketDetail).
import type { Ticket } from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface Props { tickets: Ticket[]; selectedId: string | null; onSelect: (id: string) => void }

export function TicketList({ tickets, selectedId, onSelect }: Props) {
  if (tickets.length === 0) return <p className="muted">No tickets match this filter.</p>;
  return (
    <table className="table">
      <thead><tr><th>Id</th><th>Ticket</th><th>Status</th></tr></thead>
      <tbody>
        {tickets.map((t) => (
          <tr key={t.id} className={t.id === selectedId ? "row--selected" : ""}>
            <td><button className="link" onClick={() => onSelect(t.id)}>{t.id}</button></td>
            <td className="clip">{t.text}</td>
            <td><StatusBadge status={t.status} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
