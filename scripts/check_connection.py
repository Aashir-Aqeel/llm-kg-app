import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(override=True)

uri = os.getenv("NEO4J_URI", "")
user = os.getenv("NEO4J_USER", "neo4j")
pwd  = os.getenv("NEO4J_PASSWORD", "")

print("Using URI:", uri)
driver = GraphDatabase.driver(uri, auth=(user, pwd))
with driver.session() as s:
    print(s.run("RETURN 1 AS ok").single()["ok"])
driver.close()
