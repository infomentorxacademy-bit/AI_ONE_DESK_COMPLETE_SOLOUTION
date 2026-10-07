"""tests/test_servers.py : the three MCP servers, tool by tool (in-process, no LLM, no agent)."""
import re

import pytest
from fastmcp.exceptions import ToolError           # fastmcp: raised when a tool's inputs are invalid
from mcp.shared.exceptions import McpError         # mcp: raised when a resource/prompt request fails

LEAD = {"approver_id": "L01", "role": "support_lead"}
LEAD2 = {"approver_id": "L02", "role": "support_lead"}
FIN = {"approver_id": "F01", "role": "finance"}


async def refund(call, order_id="O1001", amount=1800, key="k1", approvals=None, ticket="T2"):
    """Helper: call issue_refund with sensible defaults."""
    return await call("orders", "issue_refund", ticket_id=ticket, order_id=order_id, amount=amount,
                      reason="test", idempotency_key=key, approvals=approvals or [])


# =============================================================== orders-server: reading
async def test_get_order_found_and_missing(call):
    assert (await call("orders", "get_order", order_id="O1001"))["order"]["price"] == 1800
    assert (await call("orders", "get_order", order_id="O9999"))["error"] == "ORDER_NOT_FOUND"

async def test_find_customer_by_name_returns_all_matches_masked(call):
    items = (await call("orders", "find_customer", query="asha rao"))["items"]       # case-insensitive
    assert sorted(i["id"] for i in items) == ["C001", "C011"]
    assert all(i["email_masked"].startswith(i["email_masked"][0] + "***@") and "city" in i for i in items)

async def test_find_customer_by_exact_email_and_empty(call):
    assert [i["id"] for i in (await call("orders", "find_customer", query="rohan2@example.com"))["items"]] == ["C002"]
    assert (await call("orders", "find_customer", query="nobody here"))["items"] == []

async def test_get_customer_masks_and_flags(call):
    customer = (await call("orders", "get_customer", customer_id="C012"))["customer"]
    assert customer["fraud_flag"] is True
    assert re.fullmatch(r"f\*\*\*@example\.com", customer["email_masked"])
    assert re.fullmatch(r"\+91-\*{5}-\*{3}\d{2}", customer["phone_masked"])
    assert "email" not in customer and "phone" not in customer                       # raw PII never crosses the wire
    assert (await call("orders", "get_customer", customer_id="C999"))["error"] == "CUSTOMER_NOT_FOUND"

async def test_list_customer_orders_only_own_newest_first(call):
    items = (await call("orders", "list_customer_orders", customer_id="C013"))["items"]
    assert [o["id"] for o in items] == ["O3003", "O1010"]
    assert all(o["customer_id"] == "C013" for o in items)

async def test_get_refund_for_order(call):
    assert (await call("orders", "get_refund_for_order", order_id="O1005"))["refund"]["id"] == "R9001"
    assert (await call("orders", "get_refund_for_order", order_id="O1001"))["refund"] is None

# =============================================================== orders-server: issue_refund
async def test_refund_auto_and_idempotent(call):
    first = await refund(call)
    assert first["created"] is True and first["refund"]["id"] == "R9002" and first["refund"]["amount"] == 1800
    again = await refund(call)                                                       # same key
    assert again["created"] is False and again["refund"]["id"] == "R9002"
    other_key = await refund(call, key="k2")                                         # new key, same order => duplicate
    assert other_key["error"] == "ALREADY_REFUNDED"

@pytest.mark.parametrize("order_id,amount,code", [
    ("O1003", 100, "NOT_DELIVERED"), ("O1005", 100, "ALREADY_REFUNDED"), ("O1004", 100, "LATE"),
    ("O1009", 50000, "OVER_PRICE"), ("O9999", 100, "NOT_DELIVERED"),
])
async def test_refund_blocked_cases(call, order_id, amount, code):
    result = await refund(call, order_id=order_id, amount=amount, key=f"k-{order_id}")
    assert result["error"] == code and "message" in result
    refund_row = (await call("orders", "get_refund_for_order", order_id=order_id))["refund"]
    assert refund_row is None or refund_row["id"] == "R9001"                         # blocked => nothing new was paid

async def test_refund_needs_lead_then_ok(call):
    blocked = await refund(call, "O1007", 2001, "k7", ticket="T9")
    assert blocked["error"] == "NEEDS_LEAD" and blocked["needs"] == ["support_lead"]
    paid = await refund(call, "O1007", 2001, "k7", [LEAD], ticket="T9")
    assert paid["created"] is True and paid["refund"]["approvals"] == [LEAD]

async def test_refund_dual_approval(call):
    r1 = await refund(call, "O1013", 30000, "k13", [LEAD], ticket="T10")
    assert r1["error"] == "NEEDS_FINANCE" and r1["needs"] == ["finance"]
    assert (await refund(call, "O1013", 30000, "k13", [LEAD, LEAD], ticket="T10"))["error"] == "BAD_APPROVALS"
    ok = await refund(call, "O1013", 30000, "k13", [LEAD, FIN], ticket="T10")
    assert ok["created"] is True

async def test_refund_rejects_unknown_or_forged_approver(call):
    # The rule function alone would accept these (a lead + a "finance" person), but the SERVER checks the
    # approvers table: L01 is a support_lead, not finance, and ZZ9 does not exist.
    forged = await refund(call, "O1013", 30000, "kx", [LEAD2, {"approver_id": "L01", "role": "finance"}], ticket="T10")
    unknown = await refund(call, "O1007", 2001, "ky", [{"approver_id": "ZZ9", "role": "support_lead"}], ticket="T9")
    assert forged["error"] == unknown["error"] == "BAD_APPROVALS"
    assert (await call("orders", "get_refund_for_order", order_id="O1013"))["refund"] is None   # nothing was paid

async def test_refund_blocked_by_active_incident(call):
    await call("ops", "link_tickets_to_incident", incident_id="INC-500", ticket_ids=["T2"])
    assert (await refund(call, ticket="T2"))["error"] == "INCIDENT_ACTIVE"

async def test_blocked_and_issued_refunds_are_audited(call):
    await refund(call, "O1003", 100, "kb", ticket="T1")
    await refund(call, "O1013", 30000, "kc", [LEAD, FIN], ticket="T10")
    trail = (await call("orders", "get_audit_trail", limit=10))["items"]
    actions = [r["action"] for r in trail]
    assert actions[:2] == ["refund_issued", "refund_blocked"]                       # newest first
    assert "L01, F01" in trail[0]["detail"] and "R9002" in trail[0]["detail"]

# =============================================================== orders-server: tickets
async def test_ticket_lifecycle_create_update_recheck(call):
    created = (await call("orders", "create_ticket", text="Where is my order?", customer_id="C002"))["ticket"]
    assert created["id"] == "T15" and created["status"] == "new"
    await call("orders", "update_ticket_status", ticket_id="T15", status="resolved", resolution="Shipped", actor="priya")
    later = (await call("orders", "get_ticket", ticket_id="T15"))["ticket"]
    assert (later["status"], later["resolution"], later["incident_id"]) == ("resolved", "Shipped", None)
    trail = (await call("orders", "get_audit_trail", ticket_id="T15"))["items"]
    assert [r["action"] for r in trail] == ["status_changed", "ticket_created"] and trail[0]["actor"] == "priya"

async def test_ticket_errors_and_status_validation(call):
    assert (await call("orders", "create_ticket", text="x", customer_id="C999"))["error"] == "CUSTOMER_NOT_FOUND"
    assert (await call("orders", "get_ticket", ticket_id="T999"))["error"] == "TICKET_NOT_FOUND"
    assert (await call("orders", "update_ticket_status", ticket_id="T999", status="resolved"))["error"] == "TICKET_NOT_FOUND"
    with pytest.raises(ToolError):                                                   # Literal type rejects bad status
        await call("orders", "update_ticket_status", ticket_id="T1", status="banana")

async def test_update_status_is_idempotent(call):
    for _ in range(3):
        await call("orders", "update_ticket_status", ticket_id="T1", status="in_progress")
    trail = (await call("orders", "get_audit_trail", ticket_id="T1"))["items"]
    assert len(trail) == 1                                                           # only ONE audit row

async def test_list_tickets_filter_limit_and_order(call):
    assert len((await call("orders", "list_tickets", status="new", limit=100))["items"]) == 26
    await call("orders", "update_ticket_status", ticket_id="T1", status="resolved")
    new = (await call("orders", "list_tickets", status="new"))["items"]
    assert len(new) == 25 and new[0]["id"] == "T2"                                   # oldest first
    assert len((await call("orders", "list_tickets", limit=3))["items"]) == 3

async def test_reply_template_resource_and_prompt(client_for):
    async with client_for("orders") as client:
        text = (await client.read_resource("reply://templates/refund_ok"))[0].text
        assert "{refund_id}" in text and len(text.split()) < 60
        with pytest.raises(McpError, match="Valid kinds"):
            await client.read_resource("reply://templates/nonsense")
        prompt = (await client.get_prompt("draft_reply", {"ticket_text": "hi", "tone": "formal"})).messages[0].content.text
        assert "UNTRUSTED" in prompt and "NEVER reveal" in prompt
        with pytest.raises(Exception):                                               # tone is Literal["warm","formal"]
            await client.get_prompt("draft_reply", {"ticket_text": "hi", "tone": "angry"})

async def test_all_seven_templates_are_short(client_for):
    kinds = ["status", "refund_ok", "refund_pending", "refund_declined", "incident", "privacy_refusal", "clarify"]
    async with client_for("orders") as client:
        for kind in kinds:
            assert len((await client.read_resource(f"reply://templates/{kind}"))[0].text.split()) < 60, kind

async def test_orders_inventory(client_for):
    async with client_for("orders") as client:
        names = {t.name for t in await client.list_tools()}
        assert names == {"get_order", "find_customer", "get_customer", "list_customer_orders", "get_refund_for_order",
                         "issue_refund", "create_ticket", "get_ticket", "update_ticket_status", "list_tickets",
                         "get_audit_trail"}
        assert [t.uriTemplate for t in await client.list_resource_templates()] == ["reply://templates/{kind}"]
        assert [p.name for p in await client.list_prompts()] == ["draft_reply"]

# =============================================================== knowledge-server
async def test_policy_text_and_sections(client_for):
    async with client_for("knowledge") as client:
        assert "30 days" in (await client.read_resource("policy://refund"))[0].text
        assert "7.2" in (await client.read_resource("policy://security"))[0].text
        assert "30 days" in (await client.read_resource("faq://returns"))[0].text
        assert (await client.read_resource("policy://refund/3.2"))[0].text.startswith("3.2 Medium refunds")
        for bad in ("9.9", "abc", "3.22"):
            with pytest.raises(McpError, match="Valid sections"):
                await client.read_resource(f"policy://refund/{bad}")

async def test_search_policy(call):
    items = (await call("knowledge", "search_policy", keyword="30 days"))["items"]
    assert items and items[0]["section"] == "2.1" and items[0]["source"] == "refund"
    assert any(i["source"] == "security" for i in (await call("knowledge", "search_policy", keyword="masked"))["items"])
    assert (await call("knowledge", "search_policy", keyword="zzzzzz"))["items"] == []
    assert (await call("knowledge", "search_policy", keyword="ab"))["error"] == "KEYWORD_TOO_SHORT"

async def test_internal_rules_are_unreachable(client_for, call):
    async with client_for("knowledge") as client:
        listed = [str(r.uri) for r in await client.list_resources()] + [t.uriTemplate for t in await client.list_resource_templates()]
        assert not any("fraud" in u or "internal" in u for u in listed)
        for uri in ("internal://fraud-rules", "policy://refund/../internal/fraud-rules.md", "file:///data/internal/fraud-rules.md"):
            with pytest.raises(Exception):
                await client.read_resource(uri)
    hits = (await call("knowledge", "search_policy", keyword="Flag accounts"))["items"]
    assert hits == []                                                                # search never reads internal files

async def test_knowledge_inventory_and_prompt(client_for):
    async with client_for("knowledge") as client:
        assert [t.name for t in await client.list_tools()] == ["search_policy"]
        assert {str(r.uri) for r in await client.list_resources()} == {"policy://refund", "policy://security", "faq://returns"}
        assert [t.uriTemplate for t in await client.list_resource_templates()] == ["policy://refund/{section}"]
        prompt = (await client.get_prompt("answer_policy_question", {"question": "q"})).messages[0].content.text
        assert "I am not sure, a support lead will help" in prompt

# =============================================================== ops-server
async def test_deployments_newest_first(call):
    ids = [d["id"] for d in (await call("ops", "list_deployments"))["items"]]
    assert ids == ["D-301", "D-300", "D-299"]
    assert [d["id"] for d in (await call("ops", "list_deployments", service="orders-api"))["items"]] == ["D-300"]

async def test_metrics_and_spike(call):
    metrics = await call("ops", "get_metrics", service="payments-api")
    assert metrics["points"][1] == {"time": "14:05", "value": 0.4} and metrics["points"][2]["value"] == 22.8
    spike = await call("ops", "find_spike", service="payments-api")
    assert (spike["first_time"], spike["value"], spike["baseline"]) == ("14:10", 22.8, 0.4)
    assert (await call("ops", "find_spike", service="search-api"))["first_time"] is None
    assert (await call("ops", "find_spike", service="payments-api", threshold=0.5))["first_time"] == "14:10"

async def test_unknown_service_is_refused(call):
    for tool in ("get_metrics", "find_spike"):
        assert (await call("ops", tool, service="../../etc/passwd"))["error"] == "UNKNOWN_SERVICE"
    assert (await call("ops", "search_logs", service="evil", keyword="x"))["error"] == "UNKNOWN_SERVICE"

async def test_search_logs_marks_untrusted(call):
    result = await call("ops", "search_logs", service="payments-api", keyword="IGNORE previous")
    assert len(result["items"]) == 1 and "UNTRUSTED" in result["warning"]
    assert len((await call("ops", "search_logs", service="payments-api", keyword="timeout", limit=2))["items"]) == 2
    assert "warning" in await call("ops", "search_logs", service="payments-api", keyword="nothing-matches")

async def test_log_resource_is_allow_listed(client_for):
    async with client_for("ops") as client:
        assert "D-301" in (await client.read_resource("logs://payments-api/2026-10-07"))[0].text
        for bad in ("logs://evil/2026-10-07", "logs://payments-api/2026-10-08", "logs://payments-api/not-a-date",
                    "logs://payments-api/2026-10-07%0A"):
            with pytest.raises(Exception):
                await client.read_resource(bad)

async def test_link_tickets_idempotent_and_errors(call):
    first = await call("ops", "link_tickets_to_incident", incident_id="INC-500", ticket_ids=["B01", "B02"])
    assert (first["linked"], first["already_linked"]) == (["B01", "B02"], [])
    second = await call("ops", "link_tickets_to_incident", incident_id="INC-500", ticket_ids=["B01", "B02", "B03"])
    assert (second["linked"], second["already_linked"]) == (["B03"], ["B01", "B02"])
    assert (await call("orders", "get_ticket", ticket_id="B01"))["ticket"]["status"] == "linked_to_incident"
    assert (await call("orders", "get_ticket", ticket_id="B01"))["ticket"]["incident_id"] == "INC-500"
    assert (await call("ops", "link_tickets_to_incident", incident_id="INC-999", ticket_ids=["B01"]))["error"] == "INCIDENT_NOT_FOUND"
    bad = await call("ops", "link_tickets_to_incident", incident_id="INC-500", ticket_ids=["B04", "NOPE"])
    assert bad["error"] == "TICKET_NOT_FOUND"
    assert (await call("orders", "get_ticket", ticket_id="B04"))["ticket"]["status"] == "new"   # nothing half-linked

async def test_rollback_is_only_a_proposal(call):
    one = (await call("ops", "propose_rollback", deployment_id="D-301", evidence="spike"))["proposal"]
    assert (one["id"], one["status"], one["deployment_id"]) == ("RB-001", "awaiting_approval", "D-301")
    two = (await call("ops", "propose_rollback", deployment_id="D-301", evidence="again"))["proposal"]
    assert two["id"] == "RB-001" and len((await call("ops", "list_rollback_proposals"))["items"]) == 1
    assert (await call("ops", "propose_rollback", deployment_id="D-000", evidence="x"))["error"] == "DEPLOYMENT_NOT_FOUND"
    deployments = (await call("ops", "list_deployments"))["items"]
    assert len(deployments) == 3                                                    # nothing was rolled back or removed

async def test_incidents_inventory(call, client_for):
    await call("ops", "link_tickets_to_incident", incident_id="INC-500", ticket_ids=["B01", "B02"])
    open_now = (await call("ops", "list_incidents", status="open"))["items"]
    assert [(i["id"], i["ticket_count"]) for i in open_now] == [("INC-500", 2)]
    assert len((await call("ops", "list_incidents"))["items"]) == 2
    assert (await call("ops", "get_incident", incident_id="INC-500"))["incident"]["ticket_ids"] == ["B01", "B02"]
    assert (await call("ops", "get_incident", incident_id="X"))["error"] == "INCIDENT_NOT_FOUND"

async def test_runbook_resource_and_prompt(client_for):
    async with client_for("ops") as client:
        assert "PROPOSE a rollback" in (await client.read_resource("runbook://payments-gateway-timeouts"))[0].text
        eng = (await client.get_prompt("incident_note", {"incident_id": "INC-500"})).messages[0].content.text
        cust = (await client.get_prompt("incident_note", {"incident_id": "INC-500", "audience": "customers"})).messages[0].content.text
        assert "deployment id" in eng and "UNTRUSTED" in eng and "no deployment ids" in cust
        assert len(await client.list_tools()) == 9
