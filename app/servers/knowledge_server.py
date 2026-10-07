"""servers/knowledge_server.py : MCP server 2 "knowledge-server" (owner: policy team).

PROVIDES  1 tool (search_policy), 3 resources, 1 resource template, 1 prompt.
SECURITY  Serves ONLY data/policies, through a fixed allow-list in common/stores/policy_store.py.
          data/internal/fraud-rules.md is NOT registered anywhere and cannot be reached (NFR-02, S18).
HOW TO USE  python -m servers.knowledge_server
"""
from __future__ import annotations

import re                                   # standard library: validate the {section} argument
from typing import Any

from fastmcp import FastMCP                 # third-party: the MCP server framework

from common.prompts import policy_question_prompt   # common/prompts.py: answer_policy_question wording
from common.responses import error, items            # common/responses.py: standard result shapes
from common.stores import policy_store               # common/stores/policy_store.py: read + search policy files

mcp = FastMCP("knowledge-server")
_SECTION = re.compile(r"\d\.\d")             # a rule number such as 3.2 (matched with fullmatch)


@mcp.resource("policy://refund")
def refund_policy() -> str:
    """The whole TechNova refund policy (rules 1.1 to 6.1)."""
    return policy_store.read_document("refund")


@mcp.resource("policy://security")
def security_policy() -> str:
    """The whole security policy (rules 7.1 to 7.5)."""
    return policy_store.read_document("security")


@mcp.resource("faq://returns")
def returns_faq() -> str:
    """The customer-friendly returns FAQ."""
    return policy_store.read_document("faq")


@mcp.resource("policy://refund/{section}")
def refund_policy_section(section: str) -> str:
    """One numbered refund rule, for example 3.2. Fails with a list of valid sections if it does not exist."""
    sections = policy_store.refund_sections()
    if not _SECTION.fullmatch(section) or section not in sections:
        raise ValueError(f"Unknown section '{section}'. Valid sections: {', '.join(sections)}")
    return f"{section} {sections[section]}"


@mcp.tool
def search_policy(keyword: str) -> dict[str, Any]:
    """Search the refund and security policies for a keyword (at least 3 characters).
    Returns {"items": [{"source", "section", "text"}]}; quote the section number when you answer."""
    if len(keyword.strip()) < 3:
        return error("KEYWORD_TOO_SHORT", "Keyword must have at least 3 characters.")
    return items(policy_store.search(keyword.strip()))


@mcp.prompt
def answer_policy_question(question: str) -> str:
    """Instruction: answer ONLY from the attached policy, quote the rule number, never invent rules."""
    return policy_question_prompt(question)


if __name__ == "__main__":
    mcp.run(show_banner=False, log_level="WARNING")   # stdio transport; quiet start-up
