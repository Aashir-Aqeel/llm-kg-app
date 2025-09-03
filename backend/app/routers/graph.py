from fastapi import APIRouter
from pydantic import BaseModel
from ..services.neo4j_client import run_cypher

router = APIRouter(prefix="/graph", tags=["graph"])

class RunCypher(BaseModel):
    query: str
    params: dict = {}

@router.post("/run")
def run(payload: RunCypher):
    return run_cypher(payload.query, payload.params)
