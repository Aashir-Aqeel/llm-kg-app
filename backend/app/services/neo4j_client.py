# backend/app/services/neo4j_client.py
from __future__ import annotations
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionError
from neo4j.graph import Node, Relationship, Path
from app.core.config import settings

# Build a driver with short-lived connections to avoid stale sockets.
_DRIVER = None
def _build_driver():
    # Use your URI from .env, e.g. bolt+ssc://...:7687 (good on inspected networks)
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        # These help in networks that close idle connections
        keep_alive=True,                 # ping periodically
        max_connection_lifetime=60,      # seconds
        max_connection_pool_size=10,
    )

def _get_driver():
    global _DRIVER
    if _DRIVER is None:
        _DRIVER = _build_driver()
        _DRIVER.verify_connectivity()
    return _DRIVER

def _reset_driver():
    global _DRIVER
    if _DRIVER is not None:
        try:
            _DRIVER.close()
        except Exception:
            pass
    _DRIVER = _build_driver()
    _DRIVER.verify_connectivity()

def _serialize(value):
    if isinstance(value, Node):
        return {"labels": list(value.labels), "element_id": value.element_id, "properties": dict(value)}
    if isinstance(value, Relationship):
        return {
            "type": value.type,
            "element_id": value.element_id,
            "start_element_id": value.start_node.element_id,
            "end_element_id": value.end_node.element_id,
            "properties": dict(value),
        }
    if isinstance(value, Path):
        return {
            "nodes": [_serialize(n) for n in value.nodes],
            "relationships": [_serialize(r) for r in value.relationships],
        }
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value

def run_cypher(query: str, params: dict | None = None, database: str = "neo4j"):
    # Retry once on transient socket issues (stale/defunct connection)
    for attempt in (1, 2):
        try:
            drv = _get_driver()
            with drv.session(database=database) as session:
                result = session.run(query, params or {})
                rows = []
                for record in result:
                    rows.append({k: _serialize(v) for k, v in record.items()})
                return rows
        except (ServiceUnavailable, SessionError, OSError) as e:
            if attempt == 2:
                raise
            # Rebuild the driver and retry
            _reset_driver()
            time.sleep(0.2)
