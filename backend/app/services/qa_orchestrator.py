# backend/app/services/qa_orchestrator.py
from openai import OpenAI
from ..core.config import settings
from app.services.nl2cypher import nl_to_cypher
from app.services.neo4j_client import run_cypher

client = OpenAI(api_key=settings.OPENAI_API_KEY)

ANSWER_SYS = """You are a precise assistant. Use GRAPH_RESULTS to answer briefly.
If data is empty, say you found no matches."""

def answer_question(user_text: str):
    cypher = nl_to_cypher(user_text)
    rows = run_cypher(cypher)
    resp = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role":"system","content":ANSWER_SYS},
            {"role":"user","content":f"Question: {user_text}\nCypher:\n{cypher}\nGRAPH_RESULTS:\n{rows}"},
        ],
    )
    return {
        "cypher": cypher,
        "graph_results": rows,
        "answer": resp.choices[0].message.content.strip(),
    }
