"""Provider-neutral LLM boundary used only inside LangGraph nodes."""
from __future__ import annotations
import json
import os
import urllib.request
from .prompts import REPORT_SYSTEM_PROMPT


def generate_grounded_summary(evidence: list[dict]) -> dict:
    """Returns a cited draft. No configured model means explicit evidence-only mode."""
    source = [{"page": e["page"], "chunk_id": e["chunk_id"],
               "text": e["text"][:1800]} for e in evidence]
    provider = os.getenv("FINSIGHT_LLM_PROVIDER", "none")
    if provider == "none":
        return {"mode": "evidence_only", "text": None, "citations": source}
    if provider != "openai_compatible":
        raise ValueError(f"Unsupported FINSIGHT_LLM_PROVIDER: {provider}")
    payload = {"model": os.environ["FINSIGHT_LLM_MODEL"], "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": REPORT_SYSTEM_PROMPT}, {
        "role": "user", "content": "Create a concise executive summary. Return JSON with `text` and `citation_chunk_ids`. Evidence:\n" + json.dumps(source)}]}
    request = urllib.request.Request(os.environ["FINSIGHT_LLM_BASE_URL"].rstrip("/") + "/chat/completions", data=json.dumps(
        payload).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.getenv('FINSIGHT_LLM_API_KEY', 'ollama')}"})
    with urllib.request.urlopen(request, timeout=90) as response:
        content = json.loads(json.loads(response.read())[
                             "choices"][0]["message"]["content"])
    ids = set(content.get("citation_chunk_ids", []))
    citations = [item for item in source if item["chunk_id"] in ids]
    # A weak local model may omit IDs. Do not discard the full ingestion run:
    # retain a reviewable, evidence-only summary and expose the validation failure.
    if not citations:
        return {"mode": "needs_review", "text": None, "citations": source, "warning": "LLM response omitted valid citation_chunk_ids"}
    return {"mode": "llm", "text": content["text"], "citations": citations}
