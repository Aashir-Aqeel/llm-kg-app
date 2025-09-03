# app/utils/cypher_sanitize.py
import re

WRITE_PREFIXES = re.compile(
    r"^\s*(CREATE|MERGE|DELETE|DETACH|SET|DROP|LOAD\s+CSV|START|TERMINATE|GRANT|REVOKE|INSERT|REMOVE)\b",
    re.IGNORECASE,
)

def sanitize_cypher(q: str) -> str:
    """
    - strip ```cypher ... ``` or ``` ... ``` fences
    - trim, keep only the first statement
    - block writes (return "" to mean 'do not run')
    """
    if not q:
        return ""
    q = q.strip()

    # remove fenced code blocks (```cypher ... ```)
    q = re.sub(r"^```(?:cypher)?\s*", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\s*```$", "", q)

    # keep only first statement for safety
    parts = [p.strip() for p in q.split(";") if p.strip()]
    if not parts:
        return ""
    q = parts[0]

    # disallow write ops in QA
    if WRITE_PREFIXES.match(q):
        return ""

    return q
