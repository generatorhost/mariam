from fastapi import APIRouter

from app.core.terminology import forbidden_aliases, list_official_terms

router = APIRouter(prefix="/api/terminology", tags=["terminology"])


@router.get("")
def terminology() -> dict:
    return {
        "terms": [term.model_dump() for term in list_official_terms()],
        "forbidden_aliases": sorted(forbidden_aliases()),
    }

