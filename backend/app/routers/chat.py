# app/routers/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4

from app.models.graph import IngestRequest
from app.services.kg_extractor import extract_kg
from app.graph.loaders.upsert import upsert_entities, upsert_triples
from app.services.qa_orchestrator import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])

class Ask(BaseModel):
    text: str
    user_id: str = "demo-user"

@router.post("/ask")
def ask(payload: Ask):
    source_id = f"msg:{uuid4()}"

    # Always produce a mapping (no blocking). If extractor fails we keep it empty.
    kg_delta_dict = extract_kg(payload.user_id, payload.text, source_id=source_id) or {"entities": [], "triples": []}

    # Validate against our Pydantic schema; if it fails, use an empty delta
    try:
        kg_delta = IngestRequest(**kg_delta_dict)
    except Exception:
        kg_delta = IngestRequest(entities=[], triples=[])

    # Upsert with best-effort; failures shouldn't block response
    try:
        if kg_delta.entities:
            upsert_entities([e.model_dump() for e in kg_delta.entities])  # loader expects dicts
        if kg_delta.triples:
            upsert_triples([t.model_dump() for t in kg_delta.triples])
    except Exception:
        pass  # don’t fail the request for demo

    ans = answer_question(payload.text)

    return {
        "answer": ans.get("answer", ""),
        "cypher_used": ans.get("cypher", ""),
        "graph_results": ans.get("graph_results", []),
        "kg_delta": kg_delta.model_dump(),
        "source_id": source_id,
    }
