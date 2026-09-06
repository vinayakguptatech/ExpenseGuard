"""
LLM reasoning agent.

This runs AFTER the deterministic rule engine (policy_rules.py). Its job
is to explain violations in plain English, assign a risk score, and
suggest a next action - not to re-decide whether a rule was violated.

Uses Groq (free tier, no credit card needed - get a key at
https://console.groq.com) via the GROQ_API_KEY environment variable.
"""

import json
import os

from groq import Groq

REASONING_PROMPT = """You are a finance compliance assistant. An expense
claim was checked against policy rules. Given the invoice details and the
rule violations found, respond with ONLY a JSON object (no markdown fences):

{{
  "risk_score": "low" | "medium" | "high",
  "explanation": "1-2 plain-English sentences a non-technical finance reviewer can understand",
  "recommended_action": "auto_approve" | "hold_for_review" | "escalate_to_manager"
}}

Invoice details:
{invoice}

Violations found:
{violations}
"""


def get_risk_assessment(invoice: dict, violations: list) -> dict:
    """
    If there are no violations, short-circuits with a clean low-risk
    result and skips the API call entirely (saves quota).
    """
    if not violations:
        return {
            "risk_score": "low",
            "explanation": "No policy violations detected. Clean for auto-approval.",
            "recommended_action": "auto_approve",
        }

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = REASONING_PROMPT.format(
        invoice=json.dumps(invoice, indent=2),
        violations=json.dumps(violations, indent=2),
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.choices[0].message.content.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        severities = [v["severity"] for v in violations]
        risk = "high" if "high" in severities else "medium"
        return {
            "risk_score": risk,
            "explanation": "; ".join(v["message"] for v in violations),
            "recommended_action": "hold_for_review",
        }
