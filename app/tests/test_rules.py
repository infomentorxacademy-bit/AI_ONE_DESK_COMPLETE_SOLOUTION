"""tests/test_rules.py : the refund rules, especially the boundaries (pure Python, no DB, no LLM)."""
import pytest

from common.rules import check_refund   # common/rules.py: the single source of refund policy

TODAY = "2026-10-07"
LEAD = {"approver_id": "L01", "role": "support_lead"}
LEAD2 = {"approver_id": "L02", "role": "support_lead"}
FIN = {"approver_id": "F01", "role": "finance"}


def order(price=50000, status="delivered", delivered="2026-10-01", oid="O1"):
    return {"id": oid, "status": status, "delivered_on": delivered if status == "delivered" else None, "price": price}


def decide(amount, approvals=(), o=None, customer=None, existing=None, incident=False):
    return check_refund(o or order(), customer or {"fraud_flag": 0}, existing, amount, list(approvals), incident, TODAY)


# --- rule R1: delivered only -------------------------------------------------------------
def test_shipped_order_is_not_delivered_even_for_tiny_amount():
    assert decide(5, o=order(status="shipped"))["code"] == "NOT_DELIVERED"

def test_missing_order_is_not_delivered():
    assert check_refund(None, None, None, 100, [], False, TODAY)["code"] == "NOT_DELIVERED"

def test_cancelled_order_is_not_delivered():
    assert decide(100, o=order(status="cancelled"))["code"] == "NOT_DELIVERED"

# --- rule R4: one refund per order ---------------------------------------------------------
def test_existing_refund_is_duplicate():
    assert decide(100, existing={"id": "R9001"})["code"] == "ALREADY_REFUNDED"

def test_old_duplicate_says_duplicate_not_late():
    old = order(delivered="2026-08-01")
    assert decide(100, o=old, existing={"id": "R9001"})["code"] == "ALREADY_REFUNDED"

# --- rule R2: 30 day window ----------------------------------------------------------------
def test_day_30_is_ok():
    assert decide(100, o=order(delivered="2026-09-07"))["code"] == "OK_AUTO"       # exactly 30 days

def test_day_31_is_late():
    assert decide(100, o=order(delivered="2026-09-06"))["code"] == "LATE"          # 31 days

def test_late_beats_over_price():
    assert decide(999999, o=order(price=100, delivered="2026-08-01"))["code"] == "LATE"

# --- rule R3: amount limits ------------------------------------------------------------------
@pytest.mark.parametrize("amount", [0, -5, 50001])
def test_bad_amounts_are_over_price(amount):
    assert decide(amount)["code"] == "OVER_PRICE"

def test_full_price_is_allowed():
    assert decide(2000, o=order(price=2000))["code"] == "OK_AUTO"

# --- rule R9: open incident ----------------------------------------------------------------
def test_incident_blocks_refund():
    assert decide(100, incident=True)["code"] == "INCIDENT_ACTIVE"

def test_shipped_beats_incident():
    assert decide(100, o=order(status="shipped"), incident=True)["code"] == "NOT_DELIVERED"

# --- rules R5/R6/R7: amount tiers -------------------------------------------------------------
def test_2000_is_automatic():
    r = decide(2000)
    assert (r["code"], r["allowed"], r["needs"]) == ("OK_AUTO", True, [])

def test_2001_needs_a_lead():
    r = decide(2001)
    assert (r["code"], r["allowed"], r["needs"]) == ("NEEDS_LEAD", False, ["support_lead"])

def test_25000_needs_only_a_lead():
    assert decide(25000)["code"] == "NEEDS_LEAD"

def test_25001_needs_lead_and_finance():
    r = decide(25001)
    assert (r["code"], r["needs"]) == ("NEEDS_LEAD_AND_FINANCE", ["support_lead", "finance"])

def test_25001_with_lead_needs_finance():
    r = decide(25001, [LEAD])
    assert (r["code"], r["needs"]) == ("NEEDS_FINANCE", ["finance"])

def test_25001_with_lead_and_finance_is_approved():
    r = decide(25001, [LEAD, FIN])
    assert (r["code"], r["allowed"]) == ("OK_APPROVED", True)

def test_2001_with_lead_is_approved():
    assert decide(2001, [LEAD])["code"] == "OK_APPROVED"

def test_finance_alone_cannot_replace_a_lead():
    assert decide(2001, [FIN])["code"] == "NEEDS_LEAD"

def test_two_leads_cannot_replace_finance():
    assert decide(25001, [LEAD, LEAD2])["code"] == "NEEDS_FINANCE"

# --- approval hygiene ---------------------------------------------------------------------------
def test_same_approver_twice_is_bad():
    assert decide(25001, [LEAD, LEAD])["code"] == "BAD_APPROVALS"

def test_unknown_role_is_bad():
    assert decide(2001, [{"approver_id": "X1", "role": "intern"}])["code"] == "BAD_APPROVALS"

# --- rule R8: fraud flag ---------------------------------------------------------------------------
def test_fraud_flag_needs_lead_at_any_amount():
    r = decide(1500, customer={"fraud_flag": 1})
    assert (r["code"], r["needs"], r["flags"]) == ("NEEDS_LEAD", ["support_lead"], ["fraud_flag"])

def test_fraud_flag_with_lead_is_approved():
    assert decide(1500, [LEAD], customer={"fraud_flag": 1})["code"] == "OK_APPROVED"

def test_no_fraud_flag_means_no_flag_in_result():
    assert decide(1500)["flags"] == []

# --- shape --------------------------------------------------------------------------------------------
def test_result_always_has_the_same_keys():
    for amount in (0, 100, 5000, 30000):
        assert set(decide(amount)) == {"code", "allowed", "needs", "message", "flags"}

def test_accepts_date_objects_and_default_today():
    from datetime import date
    r = check_refund(order(delivered="2026-10-01"), {}, None, 100, [], False, date(2026, 10, 7))
    assert r["code"] == "OK_AUTO"
    assert check_refund(order(delivered="2026-10-01"), {}, None, 100, [])["code"] == "OK_AUTO"  # frozen clock
