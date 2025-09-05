from fastapi import APIRouter
from app.models.graph import CypherRunRequest, CypherRunResponse
from app.services.neo4j_client import run_cypher

router = APIRouter(prefix="/graph", tags=["graph"])

@router.post("/run", response_model=CypherRunResponse)
def run(payload: CypherRunRequest) -> CypherRunResponse:
    rows = run_cypher(payload.query, payload.params or {})
    scalar = None
    if rows:
        first = rows[0]
        if isinstance(first, dict) and len(first) == 1:
            scalar = next(iter(first.values()))
    return CypherRunResponse(rows=rows, value=scalar)
