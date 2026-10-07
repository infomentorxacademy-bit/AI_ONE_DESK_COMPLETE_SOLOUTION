"""agent/approvers.py : who answers the approval card? Two interchangeable "human" implementations.

ScriptedApprover      automatic demo: lead L01 answers lead cards, finance F01 answers finance cards.
InteractiveApprover   a real person types the answer in the terminal (run_queue.py --interactive).
Both implement ONE method:  answer(card: dict) -> dict   returning the ANSWER shape of section 13.4.
USED BY run_queue.py, tests
"""
from __future__ import annotations

from typing import Any


class ScriptedApprover:
    """Approves every card using the first missing role: L01 for support_lead, F01 for finance."""

    ROLE_TO_PERSON = {"support_lead": "L01", "finance": "F01"}

    def answer(self, card: dict[str, Any]) -> dict[str, Any]:
        role = card["needs"][0]                      # roles are listed in the order they are required
        return {"action": "approve", "approver_id": self.ROLE_TO_PERSON[role], "role": role}


class InteractiveApprover:
    """Shows the card and asks a person at the keyboard. Lets you try reject / edit_amount / cancel yourself."""

    def answer(self, card: dict[str, Any]) -> dict[str, Any]:
        print("\n  +-- APPROVAL CARD " + "-" * 40)
        for key in ("ticket_id", "order_id", "item", "amount", "needs", "rule", "flags", "recommendation"):
            print(f"  | {key:<15}{card[key]}")
        print("  +" + "-" * 56)
        action = input(f"  action {card['allowed_actions']}: ").strip().lower()
        if action == "cancel" or action not in card["allowed_actions"]:
            return {"action": "cancel"}
        role = card["needs"][0]
        approver_id = input(f"  your approver id for role {role} (e.g. L01 / L02 / F01): ").strip()
        answer: dict[str, Any] = {"action": action, "approver_id": approver_id, "role": role}
        if action == "edit_amount":
            answer["amount"] = int(input("  new amount in rupees: "))
        return answer
