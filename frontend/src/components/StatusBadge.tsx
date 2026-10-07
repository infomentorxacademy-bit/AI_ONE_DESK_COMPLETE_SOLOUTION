// components/StatusBadge.tsx : a coloured pill showing a ticket status (e.g. "pending approval").
// Used by: TicketList, TicketDetail, RunPanel. Colour comes from the CSS class "badge--<status>" in global.css.
import type { TicketStatus } from "../api/types";

export function StatusBadge({ status }: { status: TicketStatus | string }) {
  return <span className={`badge badge--${status}`}>{status.replaceAll("_", " ")}</span>;
}
