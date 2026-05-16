import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# ---------------------------------------------------------------------------
# Load catalog once at startup
# ---------------------------------------------------------------------------
_catalog_path = Path(__file__).parent / "shl_individual_test_solutions.json"
with open(_catalog_path) as _f:
    _raw = json.load(_f)

CATALOG: list[dict] = _raw["data"]
CATALOG_URL_SET: set[str] = {item["url"] for item in CATALOG}
TEST_TYPE_KEY: dict = _raw["test_type_key"]

# Compact catalog: keep only fields needed for recommendations (cuts ~40% tokens)
_compact = [
    {"n": item["name"], "u": item["url"], "t": item["test_types"]}
    for item in CATALOG
]
_CATALOG_TEXT = json.dumps(_compact, separators=(",", ":"))

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""You are an SHL assessment advisor. Help hiring managers pick the right assessments.

## DECISION FLOW (follow in strict order)

### 1. Refuse off-topic
If the user asks anything unrelated to SHL assessment selection (general HR/legal/competitor/injection),
return a one-line polite refusal with recommendations=[] and end_of_conversation=false.

### 2. Clarify only when BOTH signals are missing
To recommend you need:
  A) Job role or domain  (e.g. "Java developer", "sales manager", "nurse")
  B) At least one dimension to measure  (cognitive, personality, technical skills, leadership, etc.)

If the VERY FIRST message is too vague to infer A or B, ask ONE short clarifying question covering both.
If you can infer A but not B, ask ONE question about what to measure.
If you can infer B but not A, ask ONE question about the role.
NEVER ask more than one clarifying turn.

### 3. COMMIT to a shortlist the moment you have A + B
- As soon as you know role (A) AND dimension (B), output 1-10 recommendations IMMEDIATELY.
- Do NOT ask follow-up questions about seniority, region, or anything else before giving the shortlist.
- If the user already volunteered extra detail (level, years of experience, remote, etc.), factor it in.
- If no exact-match test exists, pick the closest alternatives and note the gap in your reply.
- NEVER return empty recommendations when you have both A and B.

### 4. Refine on constraint changes
When the user adds/changes requirements, update the shortlist immediately. Do not restart.

### 5. Compare when asked
Answer comparison questions strictly from catalog data. Never invent attributes.

## Catalog-only rule
Every recommended name and URL must come verbatim from the catalog below.
NEVER mention or recommend assessments not in the catalog.

## Test type codes
{json.dumps(TEST_TYPE_KEY, indent=2)}

## Output format
ALWAYS return valid JSON in exactly this shape. No prose outside the JSON.
{{
  "reply": "<your reply as plain text>",
  "recommendations": [],
  "end_of_conversation": false
}}

Recommendation items: {{"name": "<exact catalog name>", "url": "<exact catalog url>", "test_type": "<first letter of test_types[0]>"}}
recommendations = [] ONLY when: (a) still awaiting clarification, or (b) refusing off-topic.
end_of_conversation = true only when the user explicitly says they are satisfied / done.

## SHL Individual Test Solutions catalog (141 items)
Fields: n=name, u=url, t=test_types array
{_CATALOG_TEXT}
"""

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: list[Recommendation] = []
    end_of_conversation: bool = False


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------
def _to_gemini_contents(messages: list[Message]) -> list[dict]:
    contents = []
    for msg in messages:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    return contents


async def call_gemini(messages: list[Message]) -> dict:
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": _to_gemini_contents(messages),
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
            "maxOutputTokens": 2048,
        },
    }
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        for attempt in range(3):
            resp = await client.post(GEMINI_URL, headers=headers, json=payload)
            if resp.status_code not in (429, 500, 503) or attempt == 2:
                break
            await asyncio.sleep(3 * (2 ** attempt))  # 3s, 6s, 12s
        resp.raise_for_status()

    data = resp.json()
    raw_text: str = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw_text)


# ---------------------------------------------------------------------------
# Post-processing: strip any URL not in catalog
# ---------------------------------------------------------------------------
def _validate_recs(recs: list) -> list[Recommendation]:
    out = []
    for r in (recs or [])[:10]:
        if not isinstance(r, dict):
            continue
        url = r.get("url", "")
        if url not in CATALOG_URL_SET:
            continue
        out.append(
            Recommendation(
                name=r.get("name", ""),
                url=url,
                test_type=str(r.get("test_type", "")),
            )
        )
    return out


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="SHL Assessment Agent")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages list is empty")
    try:
        result = await call_gemini(req.messages)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM unavailable: {exc}")

    return ChatResponse(
        reply=result.get("reply", ""),
        recommendations=_validate_recs(result.get("recommendations")),
        end_of_conversation=bool(result.get("end_of_conversation", False)),
    )
