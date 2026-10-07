"""api/schemas.py : the JSON shapes the API accepts and returns (pydantic models).

WHY    FastAPI uses these to validate every request automatically (a bad body gets a clear 422 error)
       and to generate the interactive docs at /docs. They are the contract with the React UI
       (frontend/src/api/types.ts mirrors them).
USED BY api/routers/*.py
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator   # pydantic: request validation


class SelectLlmRequest(BaseModel):
    """Body of POST /api/llm : which provider to use from now on."""
    provider: Literal["openai", "groq"]


class CreateTicketRequest(BaseModel):
    """Body of POST /api/tickets."""
    text: str = Field(min_length=3, max_length=2000)
    customer_id: str | None = Field(default=None, pattern=r"^C\d{3}$")


class ApprovalAnswer(BaseModel):
    """Body of POST /api/approvals/{thread_id} : the human's decision on an approval card (spec section 13.4)."""
    action: Literal["approve", "reject", "edit_amount", "cancel"]
    approver_id: str | None = Field(default=None, pattern=r"^[LF]\d{2}$")
    role: Literal["support_lead", "finance"] | None = None
    amount: int | None = Field(default=None, gt=0, le=10_000_000)

    @model_validator(mode="after")
    def _check_required_fields(self) -> "ApprovalAnswer":
        """Everything except cancel must say WHO decided; edit_amount must also give the new amount."""
        if self.action != "cancel" and not (self.approver_id and self.role):
            raise ValueError("approver_id and role are required for approve, reject and edit_amount")
        if self.action == "edit_amount" and self.amount is None:
            raise ValueError("amount is required for edit_amount")
        return self


class RunResult(BaseModel):
    """What happened when a ticket was run or an approval was answered."""
    ticket_id: str
    thread_id: str
    state: Literal["finished", "paused"]            # paused = waiting for a human decision
    kind: str | None = None
    outcome: str | None = None
    final_status: str | None = None
    reply: str | None = None
    flags: list[str] = []
    card: dict[str, Any] | None = None              # the approval card when state == "paused"
