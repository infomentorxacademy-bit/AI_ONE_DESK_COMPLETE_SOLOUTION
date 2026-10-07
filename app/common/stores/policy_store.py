"""common/stores/policy_store.py : serves ONLY data/policies (refund policy, security policy, FAQ).

WHAT   read_document(), refund_sections(), search().
WHY    The knowledge-server must never expose anything outside data/policies. The file names are a
       fixed allow-list: there is no code path that turns user text into a filename, so
       data/internal/fraud-rules.md cannot be reached (NFR-02, scenario S18).
USED BY servers/knowledge_server.py
"""
from __future__ import annotations

import re                                   # standard library: parse "## 2.1 Title" headings
from typing import Any

from common.config import DATA_DIR          # common/config.py: location of the data folder

# FIXED allow-list: document key -> file name. Nothing else can ever be read.
_FILES = {"refund": "refund-policy.md", "security": "security-policy.md", "faq": "returns-faq.md"}
_HEADING = re.compile(r"^##\s+(\d\.\d)\s+(.*)$")      # a numbered rule heading, e.g. "## 3.2 Medium refunds"


def read_document(key: str) -> str:
    """Return the whole text of 'refund', 'security' or 'faq' (KeyError for anything else)."""
    return (DATA_DIR / "policies" / _FILES[key]).read_text(encoding="utf-8")


def _sections(key: str) -> dict[str, str]:
    """Parse a policy document into {"3.2": "Medium refunds. A refund from Rs 2,001 ..."}."""
    sections: dict[str, str] = {}
    current: str | None = None
    for line in read_document(key).splitlines():
        match = _HEADING.match(line)
        if match:
            current = match.group(1)
            sections[current] = match.group(2).strip() + "."   # start with the title
        elif current and line.strip():
            sections[current] += " " + line.strip()         # append the rule text
    return sections


def refund_sections() -> dict[str, str]:
    """All numbered refund rules (1.1 .. 6.1)."""
    return _sections("refund")


def search(keyword: str) -> list[dict[str, Any]]:
    """Case-insensitive keyword search over refund + security rules. Returns [{source, section, text}]."""
    needle = keyword.lower()
    hits: list[dict[str, Any]] = []
    for source in ("refund", "security"):
        for number, text in _sections(source).items():
            if needle in text.lower():
                hits.append({"source": source, "section": number, "text": text})
    return hits
