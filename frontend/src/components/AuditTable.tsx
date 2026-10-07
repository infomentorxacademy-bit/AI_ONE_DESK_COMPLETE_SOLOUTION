// components/AuditTable.tsx : a list of audit-log entries (who did what, when, why). Used by TicketDetail and AuditView.
import type { AuditEntry } from "../api/types";

export function AuditTable({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) return <p className="muted">No audit entries yet.</p>;
  return (
    <table className="table table--compact">
      <thead><tr><th>Time</th><th>Actor</th><th>Ticket</th><th>Action</th><th>Detail</th></tr></thead>
      <tbody>
        {entries.map((e, i) => (
          <tr key={`${e.ts}-${i}`}>
            <td className="nowrap">{e.ts.slice(11, 16)}</td><td>{e.actor}</td><td>{e.ticket_id ?? "—"}</td>
            <td><code>{e.action}</code></td><td className="clip">{e.detail}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
