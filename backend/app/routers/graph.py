# backend/app/routers/graph.py
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from neo4j.exceptions import Neo4jError

from app.services.neo4j_client import run_cypher
from app.utils.cypher_sanitize import sanitize_cypher

router = APIRouter(prefix="/graph", tags=["graph"])

class GraphQuery(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = None

@router.post("/run")
def graph_run(payload: GraphQuery):
    """
    Run a READ-ONLY Cypher query.
    - Strips ``` fences
    - Keeps only the first statement
    - Blocks write ops (CREATE/MERGE/DELETE/SET/etc)
    """
    q = sanitize_cypher(payload.query or "")
    if not q:
        return {"rows": [], "note": "Query was empty or blocked (writes not allowed here)."}

    try:
        rows = run_cypher(q, payload.params or {})
        return {"rows": rows}
    except Neo4jError as e:
        return {"rows": [], "error": f"{e.code}: {e.message}"}
