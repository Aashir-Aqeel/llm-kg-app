from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4

# ⬇️ change absolute "app.*" to relative
from ..services.kg_extractor import extract_kg
from ..graph.loaders.upsert import upsert_entities, upsert_triples
from ..services.qa_orchestrator import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])

class Ask(BaseModel):
    text: str
    user_id: str = "demo-user"

@router.post("/ask")
def ask(payload: Ask):
    source_id = f"msg:{uuid4()}"
    kg = extract_kg(payload.user_id, payload.text, source_id=source_id)
    upsert_entities(kg.get("entities", []))
    upsert_triples([
        {"subj": t["subj"], "rel": t["pred"], "obj": t["obj"], "props": t.get("props", {})}
        for t in kg.get("triples", [])
    ])
    ans = answer_question(payload.text)
    return {
        "answer": ans["answer"],
        "cypher_used": ans["cypher"],
        "graph_results": ans["graph_results"],
        "kg_delta": kg,
        "source_id": source_id,
    }
