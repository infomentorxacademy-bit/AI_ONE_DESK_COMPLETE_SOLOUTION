// src/api/types.ts : the shapes of the data the FastAPI backend sends and receives.
// They mirror app/api/schemas.py and the MCP tool results. Keeping them in ONE file means that if the
// backend changes, TypeScript shows exactly which components must change.

export type TicketStatus =
  | "new" | "in_progress" | "pending_approval" | "resolved" | "declined" | "escalated" | "linked_to_incident";

export interface Ticket {
  id: string;
  customer_id: string | null;
  text: string;
  created_at: string;
  status: TicketStatus;
  resolution: string | null;
  updated_at: string;
  incident_id: string | null;
}

export interface AuditEntry { ts: string; actor: string; ticket_id: string | null; action: string; detail: string }

/** The card a human sees when the agent pauses for a refund decision. */
export interface ApprovalCardData {
  ticket_id: string;
  order_id: string;
  item: string;
  amount: number;
  needs: Role[];                 // roles still missing, e.g. ["support_lead", "finance"]
  rule: string;                  // e.g. NEEDS_LEAD_AND_FINANCE
  flags: string[];               // internal flags, e.g. fraud_flag (shown to staff only)
  recommendation: string;
  allowed_actions: ApprovalAction[];
}

export type Role = "support_lead" | "finance";
export type ApprovalAction = "approve" | "reject" | "edit_amount" | "cancel";

/** What the human answers (sent to POST /api/approvals/{thread_id}). */
export interface ApprovalAnswer { action: ApprovalAction; approver_id?: string; role?: Role; amount?: number }

export interface PendingApproval { thread_id: string; ticket_id: string; card: ApprovalCardData }

export interface RunResult {
  ticket_id: string;
  thread_id: string;
  state: "finished" | "paused";
  kind: string | null;
  outcome: string | null;
  final_status: TicketStatus | null;
  reply: string | null;
  flags: string[];
  card: ApprovalCardData | null;
}

/** A customer candidate from the search (email is already masked by the server). */
export interface CustomerMatch { id: string; name: string; city: string; email_masked: string }

export interface Approver { id: string; name: string; role: Role }

export interface ProviderInfo { name: "openai" | "groq"; model: string; configured: boolean }
export interface AppConfig { llm: string | null; providers: ProviderInfo[]; reset_enabled: boolean }

export interface Incident {
  id: string; service: string; severity: string; status: string; opened: string; title: string; ticket_count: number;
}
export interface RollbackProposal { id: string; deployment_id: string; created_at: string; status: string; evidence: string }

/** Result of "Run outage detection" (Graph B). cluster_ids is empty when there is no outage. */
export interface IncidentRun {
  cluster_ids: string[];
  spike?: { first_time: string; value: number; baseline: number };
  correlated?: { id: string; version: string; at: string; minutes_before_spike: number } | null;
  incident_id?: string | null;
  flags?: string[];
  proposal?: RollbackProposal | null;
  engineer_note?: string;
  customer_message?: string;
}
