# backend/app/services/nl2cypher.py
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """You translate user questions into Cypher for a Neo4j graph.
Schema (labels & relationships):
(:Person)-[:WORKS_AT]->(:Org)
(:Person)-[:LIVES_IN]->(:Place)
(:Person)-[:MET_WITH]->(:Person)
(:Org)-[:FUNDED_BY {amountUSD, round, year}]->(:Investor)
(:Event)-[:OCCURRED_AT]->(:Place)

Rules:
- Return ONLY Cypher, no commentary.
- Use labels exactly as above.
"""

def nl_to_cypher(user_text: str) -> str:
    resp = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.1,
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":user_text}
        ],
    )
    return resp.choices[0].message.content.strip()
