"""api/routers/customers.py : find a customer (used to resolve "which Asha Rao?" tickets).

GET /api/customers/search?query=   customers whose NAME contains the text (case-insensitive) or whose EMAIL matches exactly.
Returns {id, name, city, email_masked} only: it goes through the MCP find_customer tool, so raw email and phone never
leave the server (privacy rule G4). The support agent compares the city the customer told us with these candidates.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query   # fastapi: routing, dependencies, query validation

from api.deps import get_state                   # api/deps.py: shared state dependency
from api.state import AppState                   # api/state.py: shared objects

router = APIRouter(tags=["customers"])


@router.get("/customers/search")
async def search_customers(query: str = Query(min_length=2, max_length=100),
                           state: AppState = Depends(get_state)) -> dict:
    """Candidates for a name or an exact email address."""
    return await state.belt.call("find_customer", query=query)
