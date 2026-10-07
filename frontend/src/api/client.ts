// src/api/client.ts : the ONLY file that talks to the backend. Components never call fetch() themselves.
// Every function returns typed data, or throws ApiError with a human-readable message that the UI can show.
import type {
  AppConfig, Approver, ApprovalAnswer, AuditEntry, CustomerMatch, Incident, IncidentRun, PendingApproval,
  RollbackProposal, RunResult, Ticket,
} from "./types";

/** An error from the backend with a readable message (never a raw stack trace). */
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

/** FastAPI errors look like {detail: "text"}, {error, detail}, or {detail: [{msg}, ...]} for validation. */
function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg ?? "invalid input").join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError("Cannot reach the backend. Is it running on port 8000?", 0);
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(messageFrom(body, `Request failed (${response.status})`), response.status);
  return body as T;
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

export const api = {
  config: () => request<AppConfig>("/config"),
  selectLlm: (provider: string) => post<{ llm: string }>("/llm", { provider }),
  searchCustomers: (query: string) =>
    request<{ items: CustomerMatch[] }>(`/customers/search?query=${encodeURIComponent(query)}`).then((r) => r.items),
  approvers: () => request<{ items: Approver[] }>("/approvers").then((r) => r.items),

  tickets: (status?: string) =>
    request<{ items: Ticket[] }>(`/tickets?limit=100${status ? `&status=${status}` : ""}`).then((r) => r.items),
  ticket: (id: string) => request<{ ticket: Ticket; audit: AuditEntry[] }>(`/tickets/${id}`),
  createTicket: (text: string, customer_id?: string) =>
    post<{ ticket: Ticket }>("/tickets", { text, customer_id: customer_id || null }).then((r) => r.ticket),
  runTicket: (id: string, customerId?: string) =>
    post<RunResult>(`/tickets/${id}/run${customerId ? `?customer_id=${encodeURIComponent(customerId)}` : ""}`),

  approvals: () => request<{ items: PendingApproval[] }>("/approvals").then((r) => r.items),
  answerApproval: (threadId: string, answer: ApprovalAnswer) => post<RunResult>(`/approvals/${threadId}`, answer),

  runIncident: () => post<IncidentRun>("/incident/run"),
  incidents: () => request<{ items: Incident[] }>("/incidents").then((r) => r.items),
  rollbacks: () => request<{ items: RollbackProposal[] }>("/rollbacks").then((r) => r.items),

  audit: (ticketId?: string) =>
    request<{ items: AuditEntry[] }>(`/audit?limit=100${ticketId ? `&ticket_id=${ticketId}` : ""}`).then((r) => r.items),
  reset: () => post<{ counts: Record<string, number> }>("/admin/reset"),
};
