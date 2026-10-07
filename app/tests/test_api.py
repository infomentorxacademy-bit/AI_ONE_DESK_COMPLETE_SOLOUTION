"""tests/test_api.py : the FastAPI backend, end to end (real MCP servers + real graphs + test-only stand-in model).

The API is started with the test double from tests/stub_llm.py instead of a paid OpenAI/Groq call.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from tests.stub_llm import StubLLM

LEAD = {"action": "approve", "approver_id": "L01", "role": "support_lead"}
FIN = {"action": "approve", "approver_id": "F01", "role": "finance"}


@pytest.fixture(scope="module")
def client():
    """One API instance (and one set of started MCP servers) for the whole module."""
    loaded = []

    def loader(provider: str):
        if provider == "groq":
            raise RuntimeError("GROQ_API_KEY is not set.")        # simulate a missing key
        loaded.append(provider)
        return StubLLM()

    with TestClient(create_app(llm_loader=loader)) as c:
        c.loaded = loaded
        yield c


@pytest.fixture(autouse=True)
def clean_pending(client):
    """Each test starts with no paused approvals (the database itself is re-seeded by conftest.fresh_db)."""
    client.app.state.ops.pending.clear()


# ------------------------------------------------------------------------------ choosing the LLM
def test_running_without_an_llm_is_a_clear_409(client):
    client.app.state.ops.llm = None
    response = client.post("/api/tickets/T1/run")
    assert response.status_code == 409 and response.json()["error"] == "NO_LLM"

def test_config_lists_providers_without_leaking_keys(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    body = client.get("/api/config").json()
    assert {p["name"] for p in body["providers"]} == {"openai", "groq"}
    assert next(p for p in body["providers"] if p["name"] == "openai")["configured"] is True
    assert "sk-secret-value" not in client.get("/api/config").text

def test_select_llm_and_missing_key_error(client):
    assert client.post("/api/llm", json={"provider": "openai"}).json() == {"llm": "test-stub"}
    bad = client.post("/api/llm", json={"provider": "groq"})
    assert bad.status_code == 400 and "GROQ_API_KEY" in bad.json()["detail"]
    assert client.post("/api/llm", json={"provider": "grok-xai"}).status_code == 422     # only openai | groq


@pytest.fixture
def with_llm(client):
    client.post("/api/llm", json={"provider": "openai"})


# ------------------------------------------------------------------------------ tickets
def test_list_get_and_create_tickets(client):
    assert len(client.get("/api/tickets?status=new&limit=100").json()["items"]) == 26
    one = client.get("/api/tickets/T2").json()
    assert one["ticket"]["id"] == "T2" and one["audit"] == []
    assert client.get("/api/tickets/T999").status_code == 404
    created = client.post("/api/tickets", json={"text": "Where is my order O1003?", "customer_id": "C004"})
    assert created.status_code == 201 and created.json()["ticket"]["id"] == "T15"
    assert client.post("/api/tickets", json={"text": "hello there", "customer_id": "C999"}).status_code == 404
    assert client.post("/api/tickets", json={"text": "x"}).status_code == 422             # too short

def test_run_a_simple_ticket(client, with_llm):
    body = client.post("/api/tickets/T1/run").json()
    assert (body["state"], body["outcome"], body["final_status"]) == ("finished", "answered", "resolved")
    assert "shipped" in body["reply"]
    ticket = client.get("/api/tickets/T1").json()
    assert ticket["ticket"]["status"] == "resolved" and len(ticket["audit"]) >= 2

def test_run_unknown_ticket_is_404(client, with_llm):
    assert client.post("/api/tickets/T999/run").status_code == 404

def test_automatic_refund_and_injection(client, with_llm):
    refund = client.post("/api/tickets/T2/run").json()
    assert refund["outcome"] == "refund_issued" and "R9002" in refund["reply"]
    injected = client.post("/api/tickets/T6/run").json()
    assert injected["outcome"] == "ignored_injection" and "possible_injection" in injected["flags"]

# ------------------------------------------------------------------------------ approvals
def test_two_step_approval_over_http(client, with_llm):
    paused = client.post("/api/tickets/T10/run").json()
    assert paused["state"] == "paused" and paused["card"]["needs"] == ["support_lead", "finance"]
    assert client.get("/api/approvals").json()["items"][0]["thread_id"] == paused["thread_id"]
    second = client.post(f"/api/approvals/{paused['thread_id']}", json=LEAD).json()
    assert second["state"] == "paused" and second["card"]["needs"] == ["finance"]
    done = client.post(f"/api/approvals/{paused['thread_id']}", json=FIN).json()
    assert (done["state"], done["outcome"], done["final_status"]) == ("finished", "refund_issued", "resolved")
    assert client.get("/api/approvals").json()["items"] == []
    audit = client.get("/api/audit?ticket_id=T10").json()["items"]
    issued = next(r for r in audit if r["action"] == "refund_issued")
    assert "L01" in issued["detail"] and "F01" in issued["detail"]

def test_reject_and_cancel(client, with_llm):
    t3 = client.post("/api/tickets/T3/run").json()
    rejected = client.post(f"/api/approvals/{t3['thread_id']}", json={**LEAD, "action": "reject"}).json()
    assert (rejected["outcome"], rejected["final_status"]) == ("refund_declined", "declined")
    t9 = client.post("/api/tickets/T9/run").json()
    cancelled = client.post(f"/api/approvals/{t9['thread_id']}", json={"action": "cancel"}).json()
    assert (cancelled["outcome"], cancelled["final_status"]) == ("pending_approval", "pending_approval")

def test_edit_amount_over_price_is_declined(client, with_llm):
    t3 = client.post("/api/tickets/T3/run").json()
    done = client.post(f"/api/approvals/{t3['thread_id']}", json={**LEAD, "action": "edit_amount", "amount": 30000}).json()
    assert done["outcome"] == "refund_declined"

def test_approval_validation_and_unknown_thread(client, with_llm):
    assert client.post("/api/approvals/nope", json=LEAD).status_code == 404
    t9 = client.post("/api/tickets/T9/run").json()
    url = f"/api/approvals/{t9['thread_id']}"
    assert client.post(url, json={"action": "approve"}).status_code == 422                    # who approved?
    assert client.post(url, json={**LEAD, "action": "edit_amount"}).status_code == 422        # needs amount
    assert client.post(url, json={**LEAD, "approver_id": "evil"}).status_code == 422          # bad id format
    assert client.get("/api/approvals").json()["items"]                                       # still waiting

def test_forged_role_cannot_unlock_a_refund(client, with_llm):
    t10 = client.post("/api/tickets/T10/run").json()
    url = f"/api/approvals/{t10['thread_id']}"
    client.post(url, json=LEAD)
    forged = client.post(url, json={"action": "approve", "approver_id": "L02", "role": "finance"}).json()
    assert forged["outcome"] == "refund_declined"                                             # server checked the table
    assert client.get("/api/tickets/T10").json()["ticket"]["status"] == "declined"

# ------------------------------------------------------------------------------ incidents + admin
def test_incident_flow_over_http(client, with_llm):
    result = client.post("/api/incident/run").json()
    assert len(result["cluster_ids"]) == 12 and result["incident_id"] == "INC-500"
    assert result["proposal"]["status"] == "awaiting_approval" and "D-301" in result["engineer_note"]
    incidents = client.get("/api/incidents?status=open").json()["items"]
    assert incidents[0]["ticket_count"] == 12
    assert len(client.get("/api/incidents/INC-500").json()["incident"]["ticket_ids"]) == 12
    assert client.get("/api/incidents/NOPE").status_code == 404
    assert len(client.get("/api/rollbacks").json()["items"]) == 1
    assert client.post("/api/incident/run").json() == {"cluster_ids": []}                     # nothing new the 2nd time

def test_customer_search_returns_masked_candidates_with_city(client):
    items = client.get("/api/customers/search?query=Asha Rao").json()["items"]
    assert sorted((c["id"], c["city"]) for c in items) == [("C001", "Delhi"), ("C011", "Mumbai")]
    assert all("@" in c["email_masked"] and "***" in c["email_masked"] for c in items)
    assert "phone" not in str(items) and "asha1@example.com" not in str(items)
    assert client.get("/api/customers/search?query=rohan2@example.com").json()["items"][0]["id"] == "C002"
    assert client.get("/api/customers/search?query=nobody-here").json()["items"] == []
    assert client.get("/api/customers/search?query=a").status_code == 422        # too short


def test_clarification_flow_end_to_end(client, with_llm):
    first = client.post("/api/tickets/T11/run").json()
    assert first["outcome"] == "needs_clarification"
    candidates = client.get("/api/customers/search?query=Asha Rao").json()["items"]
    mumbai = next(c for c in candidates if c["city"] == "Mumbai")
    second = client.post(f"/api/tickets/T11/run?customer_id={mumbai['id']}").json()
    assert second["outcome"] == "answered" and "2026-10-09" in second["reply"]


def test_approvers_and_reset_guard(client, monkeypatch):
    assert [a["id"] for a in client.get("/api/approvers").json()["items"]] == ["F01", "L01", "L02"]
    monkeypatch.delenv("OPSDESK_ENABLE_RESET", raising=False)
    assert client.post("/api/admin/reset").status_code == 403
    monkeypatch.setenv("OPSDESK_ENABLE_RESET", "1")
    assert client.post("/api/admin/reset").json()["counts"]["tickets"] == 26

def test_api_cannot_call_money_tools(client):
    belt = client.app.state.ops.belt
    import asyncio
    with pytest.raises(PermissionError):
        asyncio.run(belt.call("issue_refund"))
