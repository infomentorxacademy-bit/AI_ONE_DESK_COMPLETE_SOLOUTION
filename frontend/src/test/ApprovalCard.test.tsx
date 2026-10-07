// test/ApprovalCard.test.tsx : the approval card builds the right answer objects and blocks invalid actions.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ApprovalCard } from "../components/ApprovalCard";
import type { ApprovalCardData, Approver } from "../api/types";

const card: ApprovalCardData = {
  ticket_id: "T10", order_id: "O1013", item: "Gaming Laptop", amount: 30000, needs: ["support_lead", "finance"],
  rule: "NEEDS_LEAD_AND_FINANCE", flags: ["fraud_flag"], recommendation: "Approve if genuine.",
  allowed_actions: ["approve", "reject", "edit_amount", "cancel"],
};
const lead: Approver = { id: "L01", name: "Meera", role: "support_lead" };
const finance: Approver = { id: "F01", name: "Kiran", role: "finance" };

test("shows the facts first and the recommendation", () => {
  render(<ApprovalCard card={card} approver={lead} busy={false} onAnswer={() => {}} />);
  expect(screen.getByText(/Gaming Laptop/)).toBeInTheDocument();
  expect(screen.getByText(/Rs 30,000/)).toBeInTheDocument();
  expect(screen.getByText("NEEDS_LEAD_AND_FINANCE")).toBeInTheDocument();
  expect(screen.getByText("fraud_flag")).toBeInTheDocument();
  expect(screen.getByText("Approve if genuine.")).toBeInTheDocument();
});

test("approve sends who approved and with which role", async () => {
  const onAnswer = vi.fn();
  render(<ApprovalCard card={card} approver={lead} busy={false} onAnswer={onAnswer} />);
  await userEvent.click(screen.getByRole("button", { name: "Approve" }));
  expect(onAnswer).toHaveBeenCalledWith({ action: "approve", approver_id: "L01", role: "support_lead" });
});

test("a role the card does not need cannot approve, and a hint explains why", () => {
  render(<ApprovalCard card={{ ...card, needs: ["finance"] }} approver={lead} busy={false} onAnswer={() => {}} />);
  expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  expect(screen.getByRole("button", { name: /Edit & approve/ })).toBeDisabled();
  expect(screen.getByText(/Switch “Acting as”/)).toBeInTheDocument();
});

test("finance can approve the finance step", async () => {
  const onAnswer = vi.fn();
  render(<ApprovalCard card={{ ...card, needs: ["finance"] }} approver={finance} busy={false} onAnswer={onAnswer} />);
  await userEvent.click(screen.getByRole("button", { name: "Approve" }));
  expect(onAnswer).toHaveBeenCalledWith({ action: "approve", approver_id: "F01", role: "finance" });
});

test("edit amount sends the new amount; invalid amounts are blocked", async () => {
  const onAnswer = vi.fn();
  render(<ApprovalCard card={card} approver={lead} busy={false} onAnswer={onAnswer} />);
  const input = screen.getByLabelText("Approve a different amount");
  await userEvent.clear(input);
  await userEvent.type(input, "abc");
  expect(screen.getByRole("button", { name: /Edit & approve/ })).toBeDisabled();
  await userEvent.clear(input);
  await userEvent.type(input, "20000");
  await userEvent.click(screen.getByRole("button", { name: /Edit & approve/ }));
  expect(onAnswer).toHaveBeenCalledWith({ action: "edit_amount", amount: 20000, approver_id: "L01", role: "support_lead" });
});

test("cancel needs no identity and everything is disabled while busy", async () => {
  const onAnswer = vi.fn();
  const { rerender } = render(<ApprovalCard card={card} approver={undefined} busy={false} onAnswer={onAnswer} />);
  await userEvent.click(screen.getByRole("button", { name: /Cancel/ }));
  expect(onAnswer).toHaveBeenCalledWith({ action: "cancel" });
  rerender(<ApprovalCard card={card} approver={lead} busy={true} onAnswer={onAnswer} />);
  expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
});
