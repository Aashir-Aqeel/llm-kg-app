# app/routers/graph_view.py
from fastapi import APIRouter, Query
from app.services.neo4j_client import run_cypher

router = APIRouter(prefix="/kg", tags=["kg"])  # <-- THIS must exist

@router.get("/graph_view")
def graph_view(user_id: str = Query(...)):
    uid = f"user:{user_id}"
    q = """
    MATCH (a {id:$uid})-[r]->(b) RETURN a,r,b
    UNION
    MATCH (a)-[r]->(b {id:$uid}) RETURN a,r,b
    """
    rows = run_cypher(q, {"uid": uid})

    nodes_by_id = {}
    def put_node(node):
        nid = node["properties"].get("id") or node["element_id"]
        nodes_by_id[nid] = {
            "id": nid,
            "label": "/".join(node["labels"]),
            "title": node["properties"].get("name", nid),
            "props": node["properties"],
        }

    edges = []
    elid_to_pid = {}
    for row in rows:
        a = row["a"]; b = row["b"]; r = row["r"]
        put_node(a); put_node(b)
        elid_to_pid[a["element_id"]] = a["properties"].get("id") or a["element_id"]
        elid_to_pid[b["element_id"]] = b["properties"].get("id") or b["element_id"]
        edges.append({
            "from": elid_to_pid.get(r["start_element_id"], r["start_element_id"]),
            "to":   elid_to_pid.get(r["end_element_id"],   r["end_element_id"]),
            "label": r["type"],
            "props": r["properties"],
        })

    return {"nodes": list(nodes_by_id.values()), "edges": edges}
