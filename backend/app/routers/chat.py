# backend/app/routers/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4

from neo4j.exceptions import Neo4jError

from app.services.kg_extractor import extract_kg
from app.graph.loaders.upsert import upsert_entities, upsert_triples
from app.services.qa_orchestrator import answer_question
from app.services.neo4j_client import run_cypher
from app.utils.cypher_sanitize import sanitize_cypher  # <- NEW

router = APIRouter(prefix="/chat", tags=["chat"])


class Ask(BaseModel):
    text: str
    user_id: str = "demo-user"  # wire your auth later


@router.post("/ask")
def ask(payload: Ask):
    """
    1) Extract triples from the user's message and upsert into Neo4j.
    2) Try a READ-ONLY QA step:
       - sanitize model-produced Cypher (strip ``` fences, keep only first stmt)
       - block writes (CREATE/MERGE/DELETE/SET/etc)
       - run safely; if anything fails, don't crash the request
    """
    source_id = f"msg:{uuid4()}"

    # ---- 1) Extraction → KG upsert ----
    kg = extract_kg(payload.user_id, payload.text, source_id=source_id)
    upsert_entities(kg.get("entities", []))
    upsert_triples(
        [
            {"subj": t["subj"], "rel": t["pred"], "obj": t["obj"], "props": t.get("props", {})}
            for t in kg.get("triples", [])
        ]
    )

    # ---- 2) QA (safe, read-only, never crash) ----
    qa_answer = "(no QA run)"
    qa_cypher = None
    qa_rows = []

    try:
        # Your existing orchestrator may return a dict with 'answer', 'cypher', 'graph_results'
        ans = answer_question(payload.text)

        # If it returns a Cypher string, sanitize it BEFORE running
        raw_cypher = None
        if isinstance(ans, dict):
            raw_cypher = ans.get("cypher")
            # keep the LLM answer if present; we'll overwrite only if we successfully run Cypher
            if isinstance(ans.get("answer"), str):
                qa_answer = ans["answer"]

        # Strip fences / block writes / keep first statement
        safe_cypher = sanitize_cypher(raw_cypher or "")
        if safe_cypher:
            qa_rows = run_cypher(safe_cypher)
            qa_cypher = safe_cypher
            # If your orchestrator didn't supply an answer, make a simple one
            if qa_answer == "(no QA run)":
                qa_answer = f"I found {len(qa_rows)} row(s)."

    except Neo4jError as e:
        # Neo4j errors should not crash the endpoint
        qa_answer = f"(qa failed: {e.code})"
        qa_cypher = qa_cypher or None
        qa_rows = []
    except Exception:
        # Any other issue (OpenAI/network/etc) — return KG delta at least
        qa_answer = "(qa skipped due to an internal error)"
        qa_cypher = None
        qa_rows = []

    return {
        "answer": qa_answer,
        "cypher_used": qa_cypher,
        "graph_results": qa_rows,
        "kg_delta": kg,
        "source_id": source_id,
    }
