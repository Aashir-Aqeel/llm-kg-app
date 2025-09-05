# app/models/graph.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---- Enumerations -----------------------------------------------------------

class NodeLabel(str, Enum):
    """Allowed node/vertex labels in the KG."""
    PERSON = "Person"
    PLACE = "Place"
    ORG = "Org"
    GOAL = "Goal"


class RelType(str, Enum):
    """Allowed relationship/edge types in the KG."""
    LIVES_IN = "LIVES_IN"
    WORKS_AT = "WORKS_AT"
    FRIEND_OF = "FRIEND_OF"
    SIBLING_OF = "SIBLING_OF"
    MET_WITH = "MET_WITH"
    HAS_GOAL = "HAS_GOAL"


# ---- Pydantic models used by routers and services --------------------------

class Entity(BaseModel):
    """
    A node to upsert.
    `id` is a stable identifier you use (e.g. "user:aashir").
    """
    id: str = Field(..., description="Stable external id, e.g. 'user:aashir'.")
    label: NodeLabel = Field(..., description="Node label constrained by NodeLabel enum.")
    name: Optional[str] = Field(None, description="Human-readable name.")
    props: Dict[str, Any] = Field(default_factory=dict, description="Additional properties.")


class Triple(BaseModel):
    """
    A relationship to upsert between two existing or to-be-upserted nodes.
    """
    subj: str = Field(..., description="Subject node id (matches Entity.id).")
    pred: RelType = Field(..., description="Relationship type constrained by RelType enum.")
    obj: str = Field(..., description="Object node id (matches Entity.id).")
    props: Dict[str, Any] = Field(default_factory=dict, description="Relationship properties.")


class IngestRequest(BaseModel):
    """
    Payload for bulk upsert of entities and triples.
    """
    entities: List[Entity] = Field(default_factory=list)
    triples: List[Triple] = Field(default_factory=list)

    class Config:
        use_enum_values = True   # serialize enums to their string values
        populate_by_name = True


class CypherRunRequest(BaseModel):
    """
    Payload to execute a Cypher query through the API.
    """
    query: str
    params: Dict[str, Any] = Field(default_factory=dict)


class CypherRunResponse(BaseModel):
    """
    Minimal response wrapper for /graph/run.
    """
    value: Optional[Any] = None
