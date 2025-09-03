from fastapi import APIRouter
from pydantic import BaseModel
from ..graph.loaders.upsert import upsert_entities, upsert_triples

router = APIRouter(prefix="/kg", tags=["kg"])

class Facts(BaseModel):
    entities: list = []
    triples: list = []

@router.post("/ingest")
def ingest(payload: Facts):
    upsert_entities(payload.entities or [])
    upsert_triples(payload.triples or [])
    return {"status": "ok", "entities": len(payload.entities or []), "triples": len(payload.triples or [])}
