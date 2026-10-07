// test/RunPanel.test.tsx : RunPanel shows the right thing for each agent result.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { RunPanel } from "../components/RunPanel";
import type { RunResult } from "../api/types";

const base: RunResult = { ticket_id: "T1", thread_id: "t", state: "finished", kind: "status", outcome: "answered",
  final_status: "resolved", reply: "Your order O1003 is shipped.", flags: [], card: null };

test("a finished run shows outcome, status badge and the drafted reply", () => {
  render(<RunPanel result={base} approver={undefined} busy={false} onAnswer={() => {}} onClarify={() => {}} />);
  expect(screen.getByText("answered")).toBeInTheDocument();
  expect(screen.getByText("resolved")).toHaveClass("badge--resolved");
  expect(screen.getByText("Your order O1003 is shipped.")).toBeInTheDocument();
});

test("needs_clarification asks for a customer id and validates its format", async () => {
  const onClarify = vi.fn();
  render(<RunPanel result={{ ...base, outcome: "needs_clarification", final_status: "in_progress" }}
                   approver={undefined} busy={false} onAnswer={() => {}} onClarify={onClarify} />);
  const button = screen.getByRole("button", { name: /Run again/ });
  await userEvent.type(screen.getByLabelText(/Which customer/), "nope");
  expect(button).toBeDisabled();
  await userEvent.clear(screen.getByLabelText(/Which customer/));
  await userEvent.type(screen.getByLabelText(/Which customer/), "c011");
  await userEvent.click(button);
  expect(onClarify).toHaveBeenCalledWith("C011");
});

test("a paused run shows the approval card", () => {
  const card = { ticket_id: "T3", order_id: "O1002", item: "TV", amount: 24000, needs: ["support_lead" as const],
    rule: "NEEDS_LEAD", flags: [], recommendation: "ok", allowed_actions: ["approve" as const] };
  render(<RunPanel result={{ ...base, state: "paused", outcome: null, card }} approver={undefined} busy={false}
                   onAnswer={() => {}} onClarify={() => {}} />);
  expect(screen.getByRole("article", { name: "Approval for T3" })).toBeInTheDocument();
});
