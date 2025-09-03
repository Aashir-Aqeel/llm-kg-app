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
