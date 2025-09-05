"""
Lightweight, centralized schema helpers for the knowledge graph.

- Defines the canonical labels/relationships (via Pydantic enums).
- Provides normalization/validation helpers used before we upsert to Neo4j.
"""
from __future__ import annotations

from typing import Iterable, List

from pydantic import ValidationError

from app.models.graph import Entity, IngestRequest, NodeLabel, RelType, Triple


CANON_LABELS: set[str] = {l.value for l in NodeLabel}
CANON_RELS: set[str] = {r.value for r in RelType}


def normalize_entity(e: Entity) -> Entity:
    """
    Return a normalized copy of an entity:
    - strip whitespace,
    - keep canonical label values (already enforced by Pydantic Enum),
    - ensure props exists (handled by default_factory).
    """
    e = e.copy(deep=True)
    e.id = e.id.strip()
    if e.name:
        e.name = e.name.strip()
    return e


def normalize_triple(t: Triple) -> Triple:
    """
    Return a normalized copy of a triple:
    - strip subj/obj ids,
    - keep canonical relationship names (already enforced by Pydantic Enum).
    """
    t = t.copy(deep=True)
    t.subj = t.subj.strip()
    t.obj = t.obj.strip()
    return t


def validate_ingest(payload: IngestRequest) -> IngestRequest:
    """
    Validate and normalize an IngestRequest using our canonical schema.

    Raises:
        ValueError / ValidationError if payload is not valid.
    """
    try:
        # Pydantic has already validated types/enums; we just normalize.
        ents: List[Entity] = [normalize_entity(e) for e in payload.entities]
        triples: List[Triple] = [normalize_triple(t) for t in payload.triples]
        return IngestRequest(entities=ents, triples=triples)
    except ValidationError as ve:  # pragma: no cover - defensive
        raise ve


def ensure_ids_exist(ids: Iterable[str]) -> None:
    """Basic sanity guard for ids (non-empty after normalization)."""
    for i in ids:
        if not i:
            raise ValueError("blank id detected after normalization")
