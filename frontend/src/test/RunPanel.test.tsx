// test/RunPanel.test.tsx : RunPanel shows the right thing for each agent result.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { api } from "../api/client";
import { RunPanel } from "../components/RunPanel";
import type { RunResult } from "../api/types";

const base: RunResult = { ticket_id: "T1", thread_id: "t", state: "finished", kind: "status", outcome: "answered",
  final_status: "resolved", reply: "Your order O1003 is shipped.", flags: [], card: null };

afterEach(() => vi.restoreAllMocks());

test("a finished run shows outcome, status badge and the drafted reply", () => {
  render(<RunPanel result={base} approver={undefined} busy={false} onAnswer={() => {}} onClarify={() => {}} ticketText="" />);
  expect(screen.getByText("answered")).toBeInTheDocument();
  expect(screen.getByText("resolved")).toHaveClass("badge--resolved");
  expect(screen.getByText("Your order O1003 is shipped.")).toBeInTheDocument();
});

test("needs_clarification searches by the name in the ticket and lets staff pick the right city", async () => {
  vi.spyOn(api, "searchCustomers").mockResolvedValue([
    { id: "C001", name: "Asha Rao", city: "Delhi", email_masked: "a***@example.com" },
    { id: "C011", name: "Asha Rao", city: "Mumbai", email_masked: "a***@example.com" },
  ]);
  const onClarify = vi.fn();
  render(<RunPanel result={{ ...base, outcome: "needs_clarification", final_status: "in_progress" }} approver={undefined}
                   busy={false} onAnswer={() => {}} onClarify={onClarify} ticketText="I am Asha Rao. When will my smart watch arrive?" />);
  expect(api.searchCustomers).toHaveBeenCalledWith("Asha Rao");                       // pre-filled from the ticket
  expect(await screen.findByText("Delhi")).toBeInTheDocument();
  const mumbai = screen.getByText("Mumbai").closest("tr")!;
  await userEvent.click(within(mumbai).getByRole("button", { name: "Use this customer" }));
  expect(onClarify).toHaveBeenCalledWith("C011");                                      // the Mumbai Asha, not the Delhi one
});

test("searching again by email works and an empty result is explained", async () => {
  vi.spyOn(api, "searchCustomers").mockResolvedValue([]);
  render(<RunPanel result={{ ...base, outcome: "needs_clarification", final_status: "in_progress" }} approver={undefined}
                   busy={false} onAnswer={() => {}} onClarify={() => {}} ticketText="Where is my watch?" />);
  await userEvent.type(screen.getByLabelText(/Search by name or exact email/), "nobody@example.com");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(api.searchCustomers).toHaveBeenCalledWith("nobody@example.com");
  expect(await screen.findByText(/No customer found/)).toBeInTheDocument();
});

test("a paused run shows the approval card", () => {
  const card = { ticket_id: "T3", order_id: "O1002", item: "TV", amount: 24000, needs: ["support_lead" as const],
    rule: "NEEDS_LEAD", flags: [], recommendation: "ok", allowed_actions: ["approve" as const] };
  render(<RunPanel result={{ ...base, state: "paused", outcome: null, card }} approver={undefined} busy={false}
                   onAnswer={() => {}} onClarify={() => {}} ticketText="" />);
  expect(screen.getByRole("article", { name: "Approval for T3" })).toBeInTheDocument();
});
