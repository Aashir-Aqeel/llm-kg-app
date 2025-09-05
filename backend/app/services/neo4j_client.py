# app/services/neo4j_client.py
from __future__ import annotations

from typing import Optional, Dict, Any, List
from neo4j import GraphDatabase, Driver
from app.core.config import settings

_driver: Optional[Driver] = None  # module-level singleton


def init_driver() -> Driver:
    """
    Create the Neo4j driver once (idempotent). Uses env from settings:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE (optional).
    """
    global _driver
    if _driver is None:
        if not settings.NEO4J_URI or not settings.NEO4J_USER or not settings.NEO4J_PASSWORD:
            raise RuntimeError("Neo4j settings missing: check NEO4J_URI/USER/PASSWORD")
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        # Optional: fail fast if unreachable
        _driver.verify_connectivity()
    return _driver


def close_driver() -> None:
    """Close and clear the global driver."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def _get_driver() -> Driver:
    """Internal accessor that ensures the driver exists."""
    return _driver or init_driver()


def run_cypher(query: str, params: Optional[Dict[str, Any]] = None,
               database: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Run a Cypher query and return a list of dict rows.
    Uses settings.NEO4J_DATABASE if database is not provided.
    """
    drv = _get_driver()
    db = database or getattr(settings, "NEO4J_DATABASE", None) or None
    with drv.session(database=db) as s:
        # Pass parameters correctly for Neo4j Python driver v5:
        res = s.run(query, parameters=(params or {}))
        return [r.data() for r in res]


def ping() -> bool:
    """Lightweight connectivity check."""
    try:
        return bool(run_cypher("RETURN 1 AS ok")[0]["ok"] == 1)
    except Exception:
        return False
