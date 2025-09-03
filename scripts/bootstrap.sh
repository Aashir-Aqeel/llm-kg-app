#!/usr/bin/env bash
# scripts/bootstrap.sh — Build a working LLM+KG backend
set -euo pipefail

mkdir -p backend/app/{core,services,routers,prompts,graph/{schema,queries,loaders},models,utils,tests}
mkdir -p data/seeds scripts docs

# ───────────────── .env example ─────────────────
cat > .env.example <<'EOF'
# Neo4j Aura (keep the +s for TLS)
NEO4J_URI=neo4j+s://<your-guid>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme

# OpenAI (use any compatible model; default below uses gpt-4o-mini)
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
EOF

# ─────────────── backend/requirements ───────────
cat > backend/requirements.txt <<'EOF'
fastapi==0.115.0
uvicorn[standard]==0.30.6
neo4j==5.24.0
openai==1.43.0
python-dotenv==1.0.1
pydantic==2.8.2
EOF

# ───────────────── app/main.py ──────────────────
cat > backend/app/main.py <<'EOF'
# backend/app/main.py
from fastapi import FastAPI
from app.routers import chat, graph, kg

app = FastAPI(title="LLM builds a Personal Knowledge Graph")

app.include_router(graph.router)
app.include_router(chat.router)
app.include_router(kg.router)

@app.get("/health")
def health():
    return {"ok": True}
EOF

# ──────────────── core/config.py ────────────────
cat > backend/app/core/config.py <<'EOF'
# backend/app/core/config.py
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # loads ../.env at runtime

class Settings(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    NEO4J_URI: str = os.getenv("NEO4J_URI", "")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

settings = Settings()
EOF

# ─────────────── services/neo4j_client.py ───────
cat > backend/app/services/neo4j_client.py <<'EOF'
# backend/app/services/neo4j_client.py
from neo4j import GraphDatabase
from app.core.config import settings

driver = GraphDatabase.driver(
    settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
)

def run_cypher(query: str, params: dict | None = None):
    with driver.session() as session:
        result = session.run(query, params or {})
        return [r.data() for r in result]
EOF

# ─────────────── prompts/triple_extract.system.txt ───────────────
cat > backend/app/prompts/triple_extract.system.txt <<'EOF'
You extract a personal knowledge graph from casual text.
Output STRICT JSON with keys: entities, triples.

Ontology (limited, do NOT invent new labels/edges):
Labels: Person, Org, Place, Event, Goal, Thing
Edges (directed, uppercase): FRIEND_OF, LIVES_IN, WORKS_AT, VISITED, MET_WITH,
WILL_START_AT, PREFERS, DISLIKES, HAS_GOAL, HAS_SKILL, BOUGHT, ATTENDED, OCCURRED_AT

Rules:
- Return ONLY JSON (no prose).
- Deduplicate entities within one response.
- IDs must be stable within the response. Use slugs when obvious (e.g., "org:acme", "place:san_francisco"), else random "tmp:<uuid4>".
- Put granular properties in "props" (e.g., {"date":"2025-09-01"} on Event).
- Each triple has: subj (entity.id), pred (edge name), obj (entity.id), props: {confidence: float 0..1, text: "evidence span"}.
- If the user is the speaker, create/assume an entity id "user:<USER_ID>" with label Person and name if known.

Example input:
"I grabbed coffee with Sara at Blue Bottle in SF yesterday. I start at Acme next Monday."

Example output:
{
  "entities":[
    {"id":"user:demo", "label":"Person", "name":"Demo User", "props":{}},
    {"id":"person:sara","label":"Person","name":"Sara","props":{}},
    {"id":"place:sf","label":"Place","name":"San Francisco","props":{}},
    {"id":"org:acme","label":"Org","name":"Acme","props":{}},
    {"id":"event:coffee","label":"Event","name":"Coffee meetup","props":{"date":"2025-09-01"}}
  ],
  "triples":[
    {"subj":"user:demo","pred":"MET_WITH","obj":"person:sara","props":{"confidence":0.86,"text":"coffee with Sara"}},
    {"subj":"event:coffee","pred":"OCCURRED_AT","obj":"place:sf","props":{"confidence":0.8,"text":"Blue Bottle in SF"}},
    {"subj":"user:demo","pred":"WILL_START_AT","obj":"org:acme","props":{"confidence":0.9,"text":"start at Acme next Monday"}}
  ]
}
EOF

# ─────────────── services/kg_extractor.py ───────
cat > backend/app/services/kg_extractor.py <<'EOF'
# backend/app/services/kg_extractor.py
from __future__ import annotations
import json, uuid, datetime as dt, pathlib
from openai import OpenAI
from app.core.config import settings

PROMPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "prompts" / "triple_extract.system.txt"
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def extract_kg(user_id: str, text: str, source_id: str | None = None) -> dict:
    """Return {'entities': [...], 'triples': [...]} using strict JSON response."""
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    source_id = source_id or f"msg:{uuid.uuid4()}"
    resp = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"USER_ID={user_id}\nTEXT={text}"},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    uid = f"user:{user_id}"
    if not any(e.get("id") == uid for e in data.get("entities", [])):
        data.setdefault("entities", []).append({"id": uid, "label": "Person", "name": user_id, "props": {}})
    for t in data.get("triples", []):
        t.setdefault("props", {})
        t["props"]["source_id"] = source_id
        t["props"]["created_at"] = _now_iso()
    return data
EOF

# ─────────────── services/nl2cypher.py (optional QA) ───────────────
cat > backend/app/services/nl2cypher.py <<'EOF'
# backend/app/services/nl2cypher.py
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """You translate user questions into Cypher for a Neo4j graph.
Schema (labels & relationships):
(:Person)-[:WORKS_AT]->(:Org)
(:Person)-[:LIVES_IN]->(:Place)
(:Person)-[:MET_WITH]->(:Person)
(:Org)-[:FUNDED_BY {amountUSD, round, year}]->(:Investor)
(:Event)-[:OCCURRED_AT]->(:Place)

Rules:
- Return ONLY Cypher, no commentary.
- Use labels exactly as above.
"""

def nl_to_cypher(user_text: str) -> str:
    resp = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.1,
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":user_text}
        ],
    )
    return resp.choices[0].message.content.strip()
EOF

# ─────────────── services/qa_orchestrator.py ───────────────
cat > backend/app/services/qa_orchestrator.py <<'EOF'
# backend/app/services/qa_orchestrator.py
from openai import OpenAI
from app.core.config import settings
from app.services.nl2cypher import nl_to_cypher
from app.services.neo4j_client import run_cypher

client = OpenAI(api_key=settings.OPENAI_API_KEY)

ANSWER_SYS = """You are a precise assistant. Use GRAPH_RESULTS to answer briefly.
If data is empty, say you found no matches."""

def answer_question(user_text: str):
    cypher = nl_to_cypher(user_text)
    rows = run_cypher(cypher)
    resp = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role":"system","content":ANSWER_SYS},
            {"role":"user","content":f"Question: {user_text}\nCypher:\n{cypher}\nGRAPH_RESULTS:\n{rows}"},
        ],
    )
    return {
        "cypher": cypher,
        "graph_results": rows,
        "answer": resp.choices[0].message.content.strip(),
    }
EOF

# ─────────────── graph/loaders/upsert.py ───────────────
cat > backend/app/graph/loaders/upsert.py <<'EOF'
# backend/app/graph/loaders/upsert.py
from app.services.neo4j_client import run_cypher

ALLOWED_LABELS = ["Person","Org","Place","Event","Goal","Thing"]
ALLOWED_RELS = [
    "FRIEND_OF","LIVES_IN","WORKS_AT","VISITED","MET_WITH",
    "WILL_START_AT","PREFERS","DISLIKES","HAS_GOAL","HAS_SKILL",
    "BOUGHT","ATTENDED","OCCURRED_AT"
]

def upsert_entities(entities: list[dict]):
    q = """
    UNWIND $ents AS e
    WITH e WHERE e.label IN $labels
    FOREACH (_ IN CASE WHEN e.label='Person' THEN [1] ELSE [] END |
      MERGE (n:Person {id:e.id}) SET n.name = coalesce(e.name, n.name), n += coalesce(e.props,{})
    )
    FOREACH (_ IN CASE WHEN e.label='Org' THEN [1] ELSE [] END |
      MERGE (n:Org {id:e.id}) SET n.name = coalesce(e.name, n.name), n += coalesce(e.props,{})
    )
    FOREACH (_ IN CASE WHEN e.label='Place' THEN [1] ELSE [] END |
      MERGE (n:Place {id:e.id}) SET n.name = coalesce(e.name, n.name), n += coalesce(e.props,{})
    )
    FOREACH (_ IN CASE WHEN e.label='Event' THEN [1] ELSE [] END |
      MERGE (n:Event {id:e.id}) SET n.name = coalesce(e.name, n.name), n += coalesce(e.props,{})
    )
    FOREACH (_ IN CASE WHEN e.label='Goal' THEN [1] ELSE [] END |
      MERGE (n:Goal {id:e.id}) SET n.name = coalesce(e.name, n.name), n += coalesce(e.props,{})
    )
    FOREACH (_ IN CASE WHEN e.label='Thing' THEN [1] ELSE [] END |
      MERGE (n:Thing {id:e.id}) SET n.name = coalesce(e.name, n.name), n += coalesce(e.props,{})
    )
    """
    run_cypher(q, {"ents": entities, "labels": ALLOWED_LABELS})

def upsert_triples(triples: list[dict]):
    q = """
    UNWIND $rels AS r
    WITH r WHERE r.rel IN $allowed
    MATCH (s {id:r.subj})
    MATCH (o {id:r.obj})

    FOREACH (_ IN CASE WHEN r.rel='WORKS_AT' THEN [1] ELSE [] END |
      MERGE (s)-[x:WORKS_AT]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='LIVES_IN' THEN [1] ELSE [] END |
      MERGE (s)-[x:LIVES_IN]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='FRIEND_OF' THEN [1] ELSE [] END |
      MERGE (s)-[x:FRIEND_OF]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='VISITED' THEN [1] ELSE [] END |
      MERGE (s)-[x:VISITED]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='MET_WITH' THEN [1] ELSE [] END |
      MERGE (s)-[x:MET_WITH]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='WILL_START_AT' THEN [1] ELSE [] END |
      MERGE (s)-[x:WILL_START_AT]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='PREFERS' THEN [1] ELSE [] END |
      MERGE (s)-[x:PREFERS]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='DISLIKES' THEN [1] ELSE [] END |
      MERGE (s)-[x:DISLIKES]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='HAS_GOAL' THEN [1] ELSE [] END |
      MERGE (s)-[x:HAS_GOAL]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='HAS_SKILL' THEN [1] ELSE [] END |
      MERGE (s)-[x:HAS_SKILL]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='BOUGHT' THEN [1] ELSE [] END |
      MERGE (s)-[x:BOUGHT]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='ATTENDED' THEN [1] ELSE [] END |
      MERGE (s)-[x:ATTENDED]->(o) SET x += coalesce(r.props,{})
    )
    FOREACH (_ IN CASE WHEN r.rel='OCCURRED_AT' THEN [1] ELSE [] END |
      MERGE (s)-[x:OCCURRED_AT]->(o) SET x += coalesce(r.props,{})
    )
    """
    run_cypher(q, {"rels": triples, "allowed": ALLOWED_RELS})
EOF

# ─────────────── routers/chat.py ───────────────
cat > backend/app/routers/chat.py <<'EOF'
# backend/app/routers/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4

from app.services.kg_extractor import extract_kg
from app.graph.loaders.upsert import upsert_entities, upsert_triples
from app.services.qa_orchestrator import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])

class Ask(BaseModel):
    text: str
    user_id: str = "demo-user"   # wire your auth later

@router.post("/ask")
def ask(payload: Ask):
    source_id = f"msg:{uuid4()}"
    kg = extract_kg(payload.user_id, payload.text, source_id=source_id)
    upsert_entities(kg.get("entities", []))
    upsert_triples([
        {"subj": t["subj"], "rel": t["pred"], "obj": t["obj"], "props": t.get("props", {})}
        for t in kg.get("triples", [])
    ])
    ans = answer_question(payload.text)  # optional QA step
    return {
        "answer": ans["answer"],
        "cypher_used": ans["cypher"],
        "graph_results": ans["graph_results"],
        "kg_delta": kg,
        "source_id": source_id,
    }
EOF

# ─────────────── routers/graph.py ───────────────
cat > backend/app/routers/graph.py <<'EOF'
# backend/app/routers/graph.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.neo4j_client import run_cypher

router = APIRouter(prefix="/graph", tags=["graph"])

class CypherPayload(BaseModel):
    query: str
    params: dict | None = None

@router.post("/run")
def run(payload: CypherPayload):
    return {"rows": run_cypher(payload.query, payload.params)}
EOF

# ─────────────── routers/kg.py (subgraph fetch) ───────────────
cat > backend/app/routers/kg.py <<'EOF'
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
EOF

# ─────────────── seed files ───────────────
cat > data/seeds/constraints.cypher <<'EOF'
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT org_id    IF NOT EXISTS FOR (o:Org)    REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT inv_id    IF NOT EXISTS FOR (i:Investor) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT place_id  IF NOT EXISTS FOR (p:Place)  REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT event_id  IF NOT EXISTS FOR (e:Event)  REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT goal_id   IF NOT EXISTS FOR (g:Goal)   REQUIRE g.id IS UNIQUE;
CREATE CONSTRAINT thing_id  IF NOT EXISTS FOR (t:Thing)  REQUIRE t.id IS UNIQUE;
EOF

cat > data/seeds/seed_core.cypher <<'EOF'
MERGE (me:Person {id:"user:demo"}) SET me.name="Demo User"
MERGE (sf:Place {id:"place:san_francisco"}) SET sf.name="San Francisco"
MERGE (acme:Org {id:"org:acme"}) SET acme.name="Acme"
MERGE (me)-[:LIVES_IN]->(sf)
MERGE (me)-[:WILL_START_AT]->(acme)
EOF

# ─────────────── helper scripts ───────────────
cat > scripts/check_connection.py <<'EOF'
# scripts/check_connection.py
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER","neo4j")
pwd  = os.getenv("NEO4J_PASSWORD","")

drv = GraphDatabase.driver(uri, auth=(user,pwd))
with drv.session() as s:
    print(s.run("RETURN 1 AS ok").single()["ok"])
drv.close()
EOF

cat > scripts/seed_neo4j.py <<'EOF'
# scripts/seed_neo4j.py
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER","neo4j")
pwd  = os.getenv("NEO4J_PASSWORD","")

drv = GraphDatabase.driver(uri, auth=(user,pwd))
with drv.session() as s:
    for path in ["data/seeds/constraints.cypher", "data/seeds/seed_core.cypher"]:
        with open(path, "r", encoding="utf-8") as f:
            q = f.read()
        print("→ Running", path)
        s.run(q)
drv.close()
print("Done.")
EOF

echo "✅ Bootstrap complete."
echo "Next:"
echo "1) cp .env.example .env  &&  edit your NEO4J_* and OPENAI_*"
echo "2) python -m venv backend/.venv && source backend/.venv/bin/activate"
echo "3) pip install -r backend/requirements.txt"
echo "4) python scripts/check_connection.py  &&  python scripts/seed_neo4j.py"
echo "5) uvicorn app.main:app --reload --port 8000  (from ./backend)"
