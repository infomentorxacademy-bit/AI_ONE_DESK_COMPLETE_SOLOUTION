"""tests/test_scenarios.py : the 24 business scenarios (S1..S24), end to end through the real graphs.

Every test uses: tests/stub_llm.py (offline test double for the model) + the 3 real MCP servers over STDIO + the real SQLite database.
S18 (internal rules unreachable) is covered in test_servers.py; S23 is the ticket_lifecycle test below.
"""
from agent.runtime import interrupt_card, resume, run_ticket, start_ticket
from agent.mcp_utils import unwrap

LEAD_L01 = {"action": "approve", "approver_id": "L01", "role": "support_lead"}
FIN_F01 = {"action": "approve", "approver_id": "F01", "role": "finance"}


async def refund_of(tools, order_id):
    """The refund row for an order (read through the real tool)."""
    return unwrap(await tools["get_refund_for_order"].ainvoke({"order_id": order_id}))["refund"]


# ------------------------------------------------------------------------------ simple paths
async def test_s1_order_status(run, ticket_of):
    out = (await run("T1")).final
    assert out["outcome"] == "answered" and "shipped" in out["reply"] and "2026-10-10" in out["reply"]
    assert "refund" not in out["reply"].lower()
    assert (await ticket_of("T1"))["status"] == "resolved"

async def test_s2_s8_s14_small_refunds_are_automatic(run, tools):
    for ticket, order, amount, refund_id in (("T2", "O1001", 1800, "R9002"), ("T8", "O1006", 2000, "R9003"),
                                             ("T14", "O1014", 1200, "R9004")):
        out = (await run(ticket)).final
        assert out["outcome"] == "refund_issued" and out["final_status"] == "resolved"
        assert refund_id in out["reply"] and str(amount) in out["reply"]
        assert (await refund_of(tools, order))["amount"] == amount

async def test_s4_duplicate_refund_is_explained(run):
    out = (await run("T4")).final
    assert out["outcome"] == "refund_duplicate" and "R9001" in out["reply"] and "completed" in out["reply"]

async def test_s5_late_refund_is_declined_with_the_reason(run, tools):
    out = (await run("T5")).final
    assert out["outcome"] == "refund_declined" and out["final_status"] == "declined" and "30-day" in out["reply"]
    assert await refund_of(tools, "O1004") is None

async def test_s6_injection_is_not_obeyed(run, tools):
    out = (await run("T6")).final
    assert out["outcome"] == "ignored_injection" and "possible_injection" in out["flags"]
    assert out["final_status"] == "escalated" and await refund_of(tools, "O1009") is None
    assert "50000" not in out["reply"]

async def test_s7_policy_answer_cites_the_rule(run):
    out = (await run("T7")).final
    assert out["outcome"] == "answered" and "2.1" in out["reply"] and "30 days" in out["reply"]

async def test_s13_privacy_request_is_refused_without_personal_data(run, tools):
    out = (await run("T13")).final
    assert out["outcome"] == "refused_privacy" and out["final_status"] == "declined"
    ravi = unwrap(await tools["get_customer"].ainvoke({"customer_id": "C013"}))["customer"]
    assert ravi["city"] not in out["reply"] and "+91" not in out["reply"] and "@" not in out["reply"]

async def test_privacy_when_order_belongs_to_someone_else(tools, ticket_graph):
    created = unwrap(await tools["create_ticket"].ainvoke(
        {"text": "Please refund order O1013 for me.", "customer_id": "C002"}))["ticket"]
    run = await run_ticket(ticket_graph, created["id"])
    assert run.final["outcome"] == "refused_privacy"
    assert await refund_of(tools, "O1013") is None

# ------------------------------------------------------------------------------ approvals
async def test_s3_one_lead_approves_then_refund_is_paid(run, tools, ticket_graph, ticket_of):
    first, config = await start_ticket(ticket_graph, "T3")
    card = interrupt_card(first)
    assert card["needs"] == ["support_lead"] and card["amount"] == 24000 and card["rule"] == "NEEDS_LEAD"
    assert card["allowed_actions"] == ["approve", "reject", "edit_amount", "cancel"]
    assert (await ticket_of("T3"))["status"] == "pending_approval"                  # waiting, nothing paid
    assert await refund_of(tools, "O1002") is None
    done = await resume(ticket_graph, config, LEAD_L01)
    assert done["outcome"] == "refund_issued" and (await refund_of(tools, "O1002"))["amount"] == 24000
    assert (await ticket_of("T3"))["status"] == "resolved"

async def test_s3_reject_declines_and_pays_nothing(run, tools, ticket_graph):
    first, config = await start_ticket(ticket_graph, "T3")
    done = await resume(ticket_graph, config, {"action": "reject", "approver_id": "L01", "role": "support_lead"})
    assert done["outcome"] == "refund_declined" and done["final_status"] == "declined"
    assert await refund_of(tools, "O1002") is None

async def test_s3_edit_amount_down_pays_the_edited_amount(tools, ticket_graph):
    first, config = await start_ticket(ticket_graph, "T3")
    done = await resume(ticket_graph, config, {**LEAD_L01, "action": "edit_amount", "amount": 20000})
    assert done["outcome"] == "refund_issued" and (await refund_of(tools, "O1002"))["amount"] == 20000

async def test_s22_edit_above_price_is_refused(tools, ticket_graph):
    first, config = await start_ticket(ticket_graph, "T3")
    done = await resume(ticket_graph, config, {**LEAD_L01, "action": "edit_amount", "amount": 30000})
    assert done["outcome"] == "refund_declined" and await refund_of(tools, "O1002") is None

async def test_s19_cancel_leaves_ticket_pending_and_resumable(tools, ticket_graph, ticket_of):
    first, config = await start_ticket(ticket_graph, "T3")
    done = await resume(ticket_graph, config, {"action": "cancel"})
    assert done["outcome"] == "pending_approval" and done["final_status"] == "pending_approval"
    assert await refund_of(tools, "O1002") is None and (await ticket_of("T3"))["status"] == "pending_approval"
    again = await run_ticket(ticket_graph, "T3", None)                               # run it again later
    assert interrupt_card(again.final)["needs"] == ["support_lead"]                  # a new card appears: resumable

async def test_s9_boundary_2001_needs_a_lead(run):
    run_ = await run("T9")
    assert run_.paused_first and run_.cards[0]["needs"] == ["support_lead"] and run_.cards[0]["amount"] == 2001

async def test_s10_two_approvers_lead_then_finance(tools, ticket_graph, ticket_of):
    first, config = await start_ticket(ticket_graph, "T10")
    assert interrupt_card(first)["needs"] == ["support_lead", "finance"]
    second = await resume(ticket_graph, config, LEAD_L01)
    assert interrupt_card(second)["needs"] == ["finance"]                            # card 2
    third = await resume(ticket_graph, config, LEAD_L01)                             # same lead AGAIN
    card3 = interrupt_card(third)
    assert card3["needs"] == ["finance"] and "duplicate_approver_rejected" in card3["flags"]
    assert await refund_of(tools, "O1013") is None
    done = await resume(ticket_graph, config, FIN_F01)
    assert done["outcome"] == "refund_issued"
    refund = await refund_of(tools, "O1013")
    assert [a["approver_id"] for a in refund["approvals"]] == ["L01", "F01"]
    trail = unwrap(await tools["get_audit_trail"].ainvoke({"ticket_id": "T10"}))["items"]
    issued = next(r for r in trail if r["action"] == "refund_issued")
    assert "L01" in issued["detail"] and "F01" in issued["detail"]
    assert (await ticket_of("T10"))["status"] == "resolved"

async def test_s12_fraud_flag_needs_a_lead_and_is_never_mentioned(tools, ticket_graph):
    first, config = await start_ticket(ticket_graph, "T12")
    card = interrupt_card(first)
    assert card["amount"] == 1500 and card["needs"] == ["support_lead"] and "fraud_flag" in card["flags"]
    done = await resume(ticket_graph, config, LEAD_L01)
    assert done["outcome"] == "refund_issued" and "fraud" not in done["reply"].lower()
    assert "review" not in done["reply"].lower()

# ------------------------------------------------------------------------------ identity + errors
async def test_s11_ambiguous_customer_then_clarified(run, tools, ticket_of):
    out = (await run("T11")).final
    assert out["outcome"] == "needs_clarification" and "city" in out["reply"]
    assert (await ticket_of("T11"))["status"] == "in_progress"
    matches = unwrap(await tools["find_customer"].ainvoke({"query": "Asha Rao"}))["items"]
    assert sorted(m["id"] for m in matches) == ["C001", "C011"]
    later = (await run("T11", customer_id="C011")).final                              # customer said "Mumbai"
    assert later["outcome"] == "answered" and "shipped" in later["reply"] and "2026-10-09" in later["reply"]
    assert (await ticket_of("T11"))["status"] == "resolved"

async def test_s21_unknown_order_is_escalated_without_crashing(tools, ticket_graph, ticket_of):
    created = unwrap(await tools["create_ticket"].ainvoke(
        {"text": "Please refund my order O9999.", "customer_id": "C002"}))["ticket"]
    out = (await run_ticket(ticket_graph, created["id"])).final
    assert out["outcome"] == "order_not_found" and "O9999" in out["reply"]
    assert (await ticket_of(created["id"]))["status"] == "escalated"

async def test_s20_running_the_same_ticket_twice_pays_once(run, tools):
    await run("T2")
    out = (await run("T2")).final                                                    # second run
    assert out["outcome"] == "refund_duplicate" and "R9002" in out["reply"]
    with_count = unwrap(await tools["get_refund_for_order"].ainvoke({"order_id": "O1001"}))
    assert with_count["refund"]["id"] == "R9002"
    # And at tool level the key itself also protects us:
    again = unwrap(await tools["issue_refund"].ainvoke({"ticket_id": "T2", "order_id": "O1001", "amount": 1800,
                                                        "reason": "r", "idempotency_key": "refund-T2-O1001",
                                                        "approvals": []}))
    assert again["created"] is False and again["refund"]["id"] == "R9002"

async def test_s23_new_ticket_handled_then_rechecked_later(tools, ticket_graph, ticket_of):
    created = unwrap(await tools["create_ticket"].ainvoke({"text": "Where is my order O1003?", "customer_id": "C004"}))["ticket"]
    assert created["id"] == "T15" and created["status"] == "new"
    await run_ticket(ticket_graph, "T15")
    later = await ticket_of("T15")                                                    # a later re-check
    assert later["status"] == "resolved" and "shipped" in later["resolution"]
    trail = unwrap(await tools["get_audit_trail"].ainvoke({"ticket_id": "T15"}))["items"]
    assert [r["action"] for r in trail][-1] == "ticket_created" and len(trail) >= 3

# ------------------------------------------------------------------------------ incident flow
async def test_s15_s17_incident_flow(run_incident_flow, tools, ticket_of):
    result = await run_incident_flow()
    assert len(result["cluster_ids"]) == 12 and result["cluster_ids"][0] == "B01"
    assert (result["spike"]["first_time"], result["spike"]["value"], result["spike"]["baseline"]) == ("14:10", 22.8, 0.4)
    assert result["correlated"]["id"] == "D-301" and result["incident_id"] == "INC-500"
    note, message = result["engineer_note"], result["customer_message"]
    assert all(token in note for token in ("INC-500", "D-301", "14:10", "22.8"))
    assert "D-301" not in message and "deployment" not in message.lower() and "API" not in message
    assert "suspicious_log_line" in result["flags"] and "NOT obeyed" in note        # S17
    for n in range(1, 13):
        assert (await ticket_of(f"B{n:02d}"))["status"] == "linked_to_incident"
    incident = unwrap(await tools["get_incident"].ainvoke({"incident_id": "INC-500"}))["incident"]
    assert len(incident["ticket_ids"]) == 12
    assert unwrap(await tools["get_refund_for_order"].ainvoke({"order_id": "O2001"}))["refund"] is None

async def test_s16_rollback_is_proposed_once_and_never_executed(run_incident_flow, tools):
    result = await run_incident_flow()
    assert (result["proposal"]["id"], result["proposal"]["status"]) == ("RB-001", "awaiting_approval")
    assert "D-301" in result["proposal"]["evidence"] and "22.8" in result["proposal"]["evidence"]
    again = await run_incident_flow()                                                 # a second run
    assert not again.get("cluster_ids")        # the tickets are no longer "new", so there is no new cluster
    proposals = unwrap(await tools["list_rollback_proposals"].ainvoke({}))["items"]
    assert len(proposals) == 1

async def test_s24_linked_ticket_gets_incident_message_and_no_refund(run_incident_flow, run, tools, ticket_of):
    await run_incident_flow()
    out = (await run("B01")).final
    assert out["outcome"] == "linked_incident" and "engineers" in out["reply"]
    assert unwrap(await tools["get_refund_for_order"].ainvoke({"order_id": "O2001"}))["refund"] is None
    assert (await ticket_of("B01"))["status"] == "linked_to_incident"

async def test_payment_ticket_before_incident_flow_is_handed_over(run, ticket_of):
    out = (await run("B01")).final
    assert out["outcome"] == "needs_incident_flow" and (await ticket_of("B01"))["status"] == "escalated"

async def test_no_incident_when_fewer_than_three_similar_tickets(tools, incident_graph):
    for n in range(3, 13):                                                            # leave only B01 and B02 as "new"
        await tools["update_ticket_status"].ainvoke({"ticket_id": f"B{n:02d}", "status": "resolved"})
    from agent.runtime import run_incident
    result = await run_incident(incident_graph)
    assert not result.get("cluster_ids") and "proposal" not in result
