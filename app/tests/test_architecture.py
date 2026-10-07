"""tests/test_architecture.py : the NON-functional rules (security, least privilege, hygiene)."""
import importlib
import pkgutil
import re
from pathlib import Path

import pytest

import agent.nodes.incident as incident_nodes
import agent.nodes.ticket as ticket_nodes
from common.repositories.tickets import TICKET_STATUSES

APP = Path(__file__).resolve().parent.parent

# NFR-06: the tool allow-list of each node, copied from requirements sections 13.2 and 13.3.
EXPECTED_TOOLS = {
    "classify": {"get_ticket", "update_ticket_status"},
    "resolve_customer": {"get_customer", "find_customer"},
    "fetch_order": {"get_order", "list_customer_orders", "get_refund_for_order"},
    "check_rules": set(), "approval_gate": {"update_ticket_status"}, "issue_refund": {"issue_refund"},
    "answer_policy": {"search_policy"}, "safe_reply": set(), "incident_reply": set(), "draft_reply": set(),
    "finish": {"update_ticket_status"},
    "collect_tickets": {"list_tickets"}, "cluster": set(),
    "correlate": {"find_spike", "list_deployments", "search_logs", "list_incidents"},
    "link_tickets": {"link_tickets_to_incident"}, "propose_rollback": {"propose_rollback"}, "draft_notes": set(),
}


def _allowed(package) -> dict[str, set[str]]:
    result = {}
    for module in pkgutil.iter_modules(package.__path__):
        mod = importlib.import_module(f"{package.__name__}.{module.name}")
        result[module.name] = set(mod.ALLOWED_TOOLS)
    return result


def test_every_node_only_gets_the_tools_listed_for_it():
    found = {**_allowed(ticket_nodes), **_allowed(incident_nodes)}
    assert found == EXPECTED_TOOLS

async def test_tool_belt_blocks_other_tools(tools):
    from agent.mcp_utils import restrict
    belt = restrict(tools, ("get_order",), "demo")
    assert (await belt.call("get_order", order_id="O1001"))["order"]["id"] == "O1001"
    with pytest.raises(PermissionError, match="may not call tool 'issue_refund'"):
        await belt.call("issue_refund", ticket_id="T1", order_id="O1001", amount=1, reason="x", idempotency_key="k")

def test_exactly_21_tools_are_exposed(tools):
    assert len(tools) == 21

def test_status_literal_matches_repository_list():
    from servers.orders_server import TicketStatus
    assert set(TicketStatus.__args__) == set(TICKET_STATUSES)

def test_no_secrets_in_source_files():
    pattern = re.compile(r"sk-[A-Za-z0-9]{16,}|gsk_[A-Za-z0-9]{16,}|api[_-]?key\s*=\s*['\"][A-Za-z0-9]{12,}")
    for path in APP.rglob("*.py"):
        if ".venv" in path.parts:
            continue
        assert not pattern.search(path.read_text(encoding="utf-8")), path

def test_env_file_is_git_ignored():
    ignore = (APP.parent / ".gitignore").read_text()
    assert ".env" in ignore.splitlines() and "opsdesk.db" in ignore

def test_every_tool_has_a_docstring_and_type_hints(tools):
    import inspect
    from servers import knowledge_server, ops_server, orders_server
    for module in (orders_server, knowledge_server, ops_server):
        for name, obj in vars(module).items():
            fn = getattr(obj, "fn", None)                      # fastmcp wraps decorated functions
            if fn is None or not inspect.isfunction(fn):
                continue
            assert fn.__doc__ and len(fn.__doc__) > 20, f"{module.__name__}.{name} needs an LLM-facing docstring"
            hints = fn.__annotations__
            assert "return" in hints and all(p in hints for p in inspect.signature(fn).parameters), name

async def test_agent_never_sees_raw_pii(tools):
    """NFR-04: scan the output of every customer-facing tool for raw emails / phones."""
    from agent.mcp_utils import unwrap
    outputs = [
        await tools["get_customer"].ainvoke({"customer_id": "C002"}),
        await tools["find_customer"].ainvoke({"query": "Rohan"}),
        await tools["list_customer_orders"].ainvoke({"customer_id": "C002"}),
        await tools["get_ticket"].ainvoke({"ticket_id": "T2"}),
    ]
    blob = " ".join(str(unwrap(o)) for o in outputs)
    assert "rohan2@example.com" not in blob and not re.search(r"\+91-\d{5}-\d{5}", blob)


def test_product_code_has_no_fake_llm():
    """The product must only use OpenAI/Groq: nothing outside tests/ may mention FakeLLM or the test stub."""
    for folder in ("agent", "common", "servers"):
        for path in (APP / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "FakeLLM" not in text and "stub_llm" not in text, path
    assert not (APP / "agent" / "llm" / "fake.py").exists()
