# app/services/kg_extractor.py
from __future__ import annotations
import os
from typing import Any, Dict, List

from app.models.graph import NodeLabel, RelType

# Use mock extractor unless explicitly told to use LLM
MODE = os.getenv("KG_EXTRACTOR_MODE", "mock").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _heuristic_extract(user_id: str, text: str, source_id: str) -> Dict[str, Any]:
    """
    Very small rule-based extractor so requests never hang.
    It recognizes 'Karachi' and 'Ragioneer' in the text.
    """
    t = text.lower()
    ents: List[Dict[str, Any]] = []
    triples: List[Dict[str, Any]] = []

    user_ent = {"id": f"user:{user_id}", "label": NodeLabel.PERSON.value, "name": user_id, "props": {}}
    ents.append(user_ent)

    if "karachi" in t:
        ents.append({"id": "place:karachi", "label": NodeLabel.PLACE.value, "name": "Karachi", "props": {}})
        triples.append({
            "subj": f"user:{user_id}",
            "pred": RelType.LIVES_IN.value,
            "obj": "place:karachi",
            "props": {"text": text, "source_id": source_id}
        })

    if "ragioneer" in t:
        ents.append({"id": "org:ragioneer", "label": NodeLabel.ORG.value, "name": "Ragioneer", "props": {}})
        triples.append({
            "subj": f"user:{user_id}",
            "pred": RelType.WORKS_AT.value,
            "obj": "org:ragioneer",
            "props": {"text": text, "source_id": source_id}
        })

    return {"entities": ents, "triples": triples}


def extract_kg(user_id: str, text: str, source_id: str) -> Dict[str, Any]:
    """
    Returns a dict shaped like IngestRequest (entities, triples).
    - If KG_EXTRACTOR_MODE != 'llm' or OPENAI_API_KEY missing -> heuristic mock
    - If 'llm', call the model but fall back to heuristic if anything takes too long.
    """
    if MODE != "llm" or not OPENAI_API_KEY:
        return _heuristic_extract(user_id, text, source_id)

    # --- If you later want the LLM path, leave this stub with a hard timeout ---
    try:
        import threading

        result: Dict[str, Any] = {}

        def do_call():
            # TODO: replace with your real LLM logic
            # Keep a quick, deterministic fallback for local dev
            nonlocal result
            result = _heuristic_extract(user_id, text, source_id)

        t = threading.Thread(target=do_call, daemon=True)
        t.start()
        t.join(timeout=8.0)   # don’t block forever
        if t.is_alive():
            # timeout -> fallback
            return _heuristic_extract(user_id, text, source_id)
        return result
    except Exception:
        return _heuristic_extract(user_id, text, source_id)
