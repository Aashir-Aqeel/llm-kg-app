"""
LLM → Cypher translator.
Exports: generate_cypher(question: str) -> str
Also aliased as: nl_to_cypher(question: str) -> str
"""
from __future__ import annotations

from openai import OpenAI
from ..core.config import settings

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

_SCHEMA_PROMPT = """
You translate user questions into a SINGLE Cypher statement against this schema.

Node labels:
- Person(id, name)
- Place(id, name)
- Org(id, name)
- Goal(id, name)

Relationships:
- LIVES_IN(Person -> Place)
- WORKS_AT(Person -> Org)
- SIBLING_OF(Person <-> Person)
- FRIEND_OF(Person <-> Person)
- HAS_GOAL(Person -> Goal)
- MET_WITH(Person -> Person)

Rules:
- Output ONLY Cypher. No prose, no markdown fences.
- Prefer matching by `id` when available (e.g. 'user:aashir'); otherwise match by `name`.
- Add a reasonable LIMIT unless the question requires all results.
"""

def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`").strip()
        if s.lower().startswith("cypher"):
            s = s.split("\n", 1)[-1].strip()
    return s

def generate_cypher(question: str) -> str:
    """Convert a natural-language question into a single Cypher statement."""
    try:
        resp = _client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SCHEMA_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.1,
        )
        txt = (resp.choices[0].message.content or "").strip()
        cypher = _strip_fences(txt)
        return cypher or "MATCH (n) RETURN n LIMIT 5"
    except Exception:
        # Keep the server alive even if OpenAI fails
        return "MATCH (n) RETURN n LIMIT 5"

# Back-compat alias used elsewhere
nl_to_cypher = generate_cypher
