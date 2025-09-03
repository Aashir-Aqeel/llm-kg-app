# scripts/seed_neo4j.py
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(override=True)

uri = os.getenv("NEO4J_URI", "")
user = os.getenv("NEO4J_USER", "neo4j")
pwd  = os.getenv("NEO4J_PASSWORD", "")

print("Using URI:", uri)
print("User:", user)

driver = GraphDatabase.driver(uri, auth=(user, pwd))

def cypher_statements_from_file(path: str):
    """
    Yield individual Cypher statements.
    - Joins multi-line statements.
    - Splits on trailing ';' (Browser style).
    - Skips empty lines and comments starting with // or #.
    """
    buf = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            buf.append(line)
            if line.endswith(";"):
                stmt = " ".join(buf).rstrip(";").strip()
                if stmt:
                    yield stmt
                buf = []
    # last statement (no semicolon at EOF)
    if buf:
        stmt = " ".join(buf).rstrip(";").strip()
        if stmt:
            yield stmt

files = ["data/seeds/constraints.cypher", "data/seeds/seed_core.cypher"]

with driver.session() as s:
    for path in files:
        print(f"→ Reading {path}")
        for stmt in cypher_statements_from_file(path):
            print("   - RUN:", stmt[:100] + ("..." if len(stmt) > 100 else ""))
            s.run(stmt)

driver.close()
print("Done.")
