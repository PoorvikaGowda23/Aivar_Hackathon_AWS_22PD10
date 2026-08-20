"""
Step 2b: LLM-assisted narrative extraction.

Only two schema fields need actual synthesis rather than a direct
read from structured input:
  - purpose_and_scope   (a readable summary of what the agent does)
  - known_limitations   (inferred from patterns in the run trace, e.g.
                          repeated failures, low-confidence outcomes)

Everything else in the card comes straight from parsers.py. Keeping the
LLM's job this narrow is deliberate: the more we ask it to invent, the
more there is to get wrong in a compliance document.

Groq is used for fast, free-tier inference (llama-3.3-70b-versatile).
The model is instructed to return JSON only, and the response is validated
against NarrativeFields below before being trusted. If it fails to
parse, we retry once with a stricter reminder before giving up.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()  # loads GROQ_API_KEY from .env in the project root

# pyrefly: ignore [missing-import]
from groq import Groq
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ValidationError

MODEL = "qwen/qwen3.6-27b"


class NarrativeFields(BaseModel):
    purpose_and_scope: str
    known_limitations: List[str]


_SYSTEM_PROMPT = """You write two fields for an AI agent compliance card, \
based on the agent's config, tool manifest, and a sample of its run trace.

Respond with ONLY a JSON object, no other text, no markdown fences, in \
exactly this shape:
{"purpose_and_scope": "<2-4 sentences describing what the agent does and its boundaries>", \
"known_limitations": ["<limitation 1>", "<limitation 2>"]}

Rules:
- purpose_and_scope must be plain, factual, non-marketing language.
- known_limitations must be grounded in the run trace you were given \
(e.g. repeated tool failures, error patterns, low-confidence outcomes). \
Do not invent limitations that are not evidenced in the data. If the \
trace shows no issues, return an empty list.
- Do not include any regulatory language or citations here — that is \
handled elsewhere.
"""


def _build_user_message(
    raw_config: Dict[str, Any],
    raw_manifest: Dict[str, Any],
    raw_trace: Dict[str, Any],
) -> str:
    return (
        "agent_config:\n" + json.dumps(raw_config, indent=2) +
        "\n\ntool_manifest:\n" + json.dumps(raw_manifest, indent=2) +
        "\n\nrun_trace:\n" + json.dumps(raw_trace, indent=2)
    )


def _call_groq(client: Groq, user_message: str, strict_retry: bool = False) -> str:
    system = _SYSTEM_PROMPT
    if strict_retry:
        system += "\n\nYour previous response was not valid JSON. Return ONLY the JSON object, nothing else."

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4000,  # enough budget for chain-of-thought + answer
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    raw = response.choices[0].message.content or ""
    # Strip <think>...</think> chain-of-thought blocks (Qwen and similar models)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # Fallback: extract the first {...} JSON block if model added surrounding text
    if raw and not raw.startswith("{"):
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        raw = match.group(0) if match else raw
    return raw


def generate_narrative_fields(
    raw_config: Dict[str, Any],
    raw_manifest: Dict[str, Any],
    raw_trace: Dict[str, Any],
) -> NarrativeFields:
    """Call Groq (Llama 3.3 70B) to produce purpose_and_scope + known_limitations, validated."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
            "and set it as an environment variable before running the generator."
        )

    client = Groq(api_key=api_key)
    user_message = _build_user_message(raw_config, raw_manifest, raw_trace)

    for attempt in range(2):  # one initial try + one strict retry
        raw_text = _call_groq(client, user_message, strict_retry=(attempt == 1))
        try:
            parsed = json.loads(raw_text)
            return NarrativeFields(**parsed)
        except (json.JSONDecodeError, ValidationError):
            if attempt == 1:
                raise RuntimeError(
                    f"Groq did not return valid JSON after retry. Last response:\n{raw_text}"
                )
            continue

    raise RuntimeError("Unreachable")  # pragma: no cover


# ══════════════════════════════════════════════════════════════════════════════
# Feature 3: AI Regulatory Auditor Review Models & Generator
# ══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone


class AuditRecommendation(BaseModel):
    category: str
    severity: str
    finding: str
    remediation: str


class AuditReport(BaseModel):
    agent_id: str
    eu_ai_act_tier: str
    audit_summary: str
    governance_gaps: List[str]
    recommendations: List[AuditRecommendation]
    audited_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.audited_at:
            self.audited_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_AUDITOR_SYSTEM_PROMPT = """You are a Senior AI Regulatory Auditor performing an audit on an AI Agent Compliance Card grounded in the EU AI Act and NIST AI RMF 1.0.

Respond with ONLY a JSON object, no markdown fences, no extra text, in this exact shape:
{
  "agent_id": "<agent_id>",
  "eu_ai_act_tier": "<e.g. High-Risk (Art. 6) / Transparency Risk (Art. 50) / General Purpose>",
  "audit_summary": "<3-4 sentence professional audit assessment of the agent card>",
  "governance_gaps": ["<gap 1>", "<gap 2>"],
  "recommendations": [
    {
      "category": "<Human Oversight | Data Privacy | Operational Autonomy | Risk Mitigation>",
      "severity": "<HIGH | MEDIUM | LOW>",
      "finding": "<specific observation from card data>",
      "remediation": "<actionable fix for developers>"
    }
  ]
}

RULES:
1. Base your evaluation strictly on the provided AgentCard JSON and score.
2. Do NOT invent tools, capabilities, or risks not present in the card.
3. Keep findings professional, actionable, and compliance-focused.
"""


def generate_audit_review(
    card_dict: Dict[str, Any],
    score_dict: Dict[str, Any],
) -> AuditReport:
    """Calls Groq API (LLaMA 3.3 70B) to generate a structured AI Regulatory Audit Report."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
            "and set it as an environment variable before running the auditor."
        )

    client = Groq(api_key=api_key)
    agent_id = card_dict.get("agent_id", "unknown")

    user_payload = (
        f"AgentCard Data:\n{json.dumps(card_dict, indent=2, default=str)}\n\n"
        f"Compliance & Risk Score Data:\n{json.dumps(score_dict, indent=2, default=str)}"
    )

    for attempt in range(2):
        system = _AUDITOR_SYSTEM_PROMPT
        if attempt == 1:
            system += "\n\nYour previous response was not valid JSON. Return ONLY the raw JSON object."

        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=4000,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_payload},
                ],
            )
            raw = response.choices[0].message.content or ""
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            if raw and not raw.startswith("{"):
                match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
                raw = match.group(0) if match else raw

            parsed = json.loads(raw)
            if "agent_id" not in parsed or not parsed["agent_id"]:
                parsed["agent_id"] = agent_id

            return AuditReport(**parsed)
        except Exception as exc:
            if attempt == 1:
                # Return a structured fallback report if LLM inference fails completely
                return AuditReport(
                    agent_id=agent_id,
                    eu_ai_act_tier="Transparency Risk (Art. 50)",
                    audit_summary=f"Automated audit fallback: Card evaluated with score {score_dict.get('overall_score', 0)}/100.",
                    governance_gaps=score_dict.get("penalties", ["Card review completed."]),
                    recommendations=[
                        AuditRecommendation(
                            category="Governance & Oversight",
                            severity="MEDIUM" if score_dict.get("overall_score", 0) >= 70 else "HIGH",
                            finding=p,
                            remediation="Update agent_config.json or tool_manifest.json to add required safeguards."
                        )
                        for p in score_dict.get("penalties", ["Review oversight controls."])[:3]
                    ],
                )
            continue

    raise RuntimeError("Unreachable")