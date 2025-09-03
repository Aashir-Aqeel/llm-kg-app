# backend/app/services/kg_extractor.py
from __future__ import annotations
import json, uuid, datetime as dt, pathlib
from openai import OpenAI
from app.core.config import settings

PROMPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "prompts" / "triple_extract.system.txt"
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def extract_kg(user_id: str, text: str, source_id: str | None = None) -> dict:
    """Return {'entities': [...], 'triples': [...]} using strict JSON response."""
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    source_id = source_id or f"msg:{uuid.uuid4()}"
    resp = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"USER_ID={user_id}\nTEXT={text}"},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    uid = f"user:{user_id}"
    if not any(e.get("id") == uid for e in data.get("entities", [])):
        data.setdefault("entities", []).append({"id": uid, "label": "Person", "name": user_id, "props": {}})
    for t in data.get("triples", []):
        t.setdefault("props", {})
        t["props"]["source_id"] = source_id
        t["props"]["created_at"] = _now_iso()
    return data
