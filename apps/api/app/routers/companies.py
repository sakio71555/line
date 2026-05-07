from __future__ import annotations

from fastapi import APIRouter, Query

from ..services.company_search import DEFAULT_COMPANY_SEARCH_LIMIT, MAX_COMPANY_SEARCH_LIMIT, search_company_cards

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/search")
def search_companies(
    q: str = "",
    limit: int = Query(default=DEFAULT_COMPANY_SEARCH_LIMIT, ge=1),
) -> dict:
    return search_company_cards(q, limit=min(limit, MAX_COMPANY_SEARCH_LIMIT))

