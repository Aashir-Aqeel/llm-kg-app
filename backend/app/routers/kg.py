# backend/app/routers/kg.py
from fastapi import APIRouter, Query
from app.services.neo4j_client import run_cypher

router = APIRouter(prefix="/kg", tags=["kg"])

@router.get("/subgraph")
def subgraph(user_id: str = Query(..., description="e.g., mubashir")):
    uid = f"user:{user_id}"
    q = """
    MATCH (me:Person {id:$uid})-[r]-(n)
    RETURN me, r, n
    """
    return {"rows": run_cypher(q, {"uid": uid})}
