"""
Helpers that write validated data into Neo4j.

We keep these functions small and side-effect free (besides the DB call),
so it's easy to test and reason about the Cypher used.
"""
from __future__ import annotations

from typing import Iterable, List

from app.models.graph import Entity, Triple
from app.services.neo4j_client import run_cypher


def upsert_entities(entities: Iterable[Entity]) -> None:
    """
    Create or update nodes by id.

    Cypher notes:
      - MERGE on {id} ensures we never duplicate nodes.
      - We set/merge the 'name' and any extra props from 'props'.
    """
    ents: List[dict] = [
        {"id": e.id, "label": e.label.value, "name": e.name, "props": e.props}
        for e in entities
    ]

    if not ents:
        return

    query = """
    UNWIND $ents AS e
    CALL {
      WITH e
      CALL apoc.merge.node([e.label], {id:e.id}, {}, {}) YIELD node
      WITH node, e
      SET node += e.props
      SET node.name = coalesce(e.name, node.name)
      RETURN count(*) AS _
    }
    RETURN 1 AS ok
    """
    run_cypher(query, {"ents": ents})


def upsert_triples(triples: Iterable[Triple]) -> None:
    """
    Create or update relationships between existing/just-created nodes.

    For each triple, we MERGE the relationship and attach edge properties.
    """
    rels: List[dict] = [
        {
            "subj": t.subj,
            "pred": t.pred.value,
            "obj": t.obj,
            "props": t.props,
        }
        for t in triples
    ]

    if not rels:
        return

    query = """
    UNWIND $rels AS r
    MATCH (s {id:r.subj})
    MATCH (o {id:r.obj})
    CALL apoc.merge.relationship(s, r.pred, {}, r.props, o) YIELD rel
    SET rel += r.props
    RETURN 1 AS ok
    """
    run_cypher(query, {"rels": rels})
