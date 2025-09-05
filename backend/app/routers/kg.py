"""Knowledge-graph ingest endpoints (manual inserts)."""
from __future__ import annotations

from fastapi import APIRouter

from app.graph.kg_schema import validate_ingest
from app.models.graph import IngestRequest
from app.graph.loaders.upsert import upsert_entities, upsert_triples

router = APIRouter(prefix="/kg", tags=["kg"])


@router.post("/ingest", summary="Upsert entities and triples into the graph")
def ingest(body: IngestRequest) -> dict:
    """
    Upsert nodes (entities) and relationships (triples).

    The payload is validated/normalized by our schema before writing.
    """
    normalized = validate_ingest(body)

    if normalized.entities:
        upsert_entities(normalized.entities)
    if normalized.triples:
        upsert_triples(normalized.triples)

    return {
        "status": "ok",
        "entities": len(normalized.entities),
        "triples": len(normalized.triples),
    }
