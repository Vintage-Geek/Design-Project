import json
import logging
from typing import Dict, Optional, List

import google.generativeai as genai

from config import config

logger = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in .env")
        genai.configure(api_key=config.GEMINI_API_KEY)
        _client = genai.GenerativeModel("gemini-2.5-flash")
    return _client


def _call_gemini(prompt: str, max_tokens: int = 512) -> str:
    """Call Gemini API and return text response."""
    model = get_client()
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens)
    )
    return response.text.strip()


def classify_outcome(transcript: str) -> Dict:
    """Use Gemini to classify call outcome from a transcript."""
    if not config.GEMINI_API_KEY or not transcript:
        return {"outcome": "unknown", "intent_tags": [], "summary": "", "language": "en"}

    prompt = f"""Analyze the following insurance payment reminder call transcript.

TRANSCRIPT:
{transcript}

Return a JSON object with EXACTLY these keys:
{{
  "outcome": one of ["paid", "promise_to_pay", "callback_requested", "unreachable", "voicemail", "disputed", "escalated", "do_not_call"],
  "intent_tags": [list of 1-5 short intent descriptors, e.g. "acknowledged_debt", "requested_extension", "denied_ownership"],
  "summary": "2-3 sentence factual summary of the call in English",
  "language": "2-letter ISO language code detected (e.g. en, hi, ta)",
  "promise_date": "YYYY-MM-DD if customer promised to pay on a specific date, else null",
  "promise_amount": "numeric amount if mentioned, else null",
  "callback_datetime": "YYYY-MM-DD HH:MM if callback scheduled, else null",
  "escalation_flag": true or false,
  "escalation_reason": "reason if escalation_flag is true, else null",
  "sentiment": one of ["positive", "neutral", "negative", "hostile"]
}}

Respond with ONLY the JSON object, no preamble or markdown backticks."""

    try:
        text = _call_gemini(prompt, max_tokens=512)
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse NLP classification JSON")
        return {"outcome": "unknown", "intent_tags": [], "summary": transcript[:200], "language": "en"}
    except Exception as e:
        logger.error("NLP classification error: %s", e)
        return {"outcome": "unknown", "intent_tags": [], "summary": "", "language": "en"}


def summarize_call(transcript: str, customer_name: str, policy_number: str, amount: float) -> str:
    """Generate a concise, structured call summary."""
    if not config.GEMINI_API_KEY or not transcript:
        return "No transcript available for summarization."

    prompt = f"""Summarize this insurance payment reminder call in 3-4 sentences.
Customer: {customer_name}
Policy: {policy_number}
Amount Due: INR {amount:,.2f}

TRANSCRIPT:
{transcript}

Write a factual, professional summary for an insurance agent's records.
Include: what was discussed, customer's response, and any next steps."""

    try:
        return _call_gemini(prompt, max_tokens=300)
    except Exception as e:
        logger.error("Summarization error: %s", e)
        return "Summary unavailable."


def calculate_priority_score(policy: Dict) -> tuple[int, str]:
    """Calculate call priority score and label based on aging rules."""
    days_overdue = policy.get("days_overdue", 0) or 0
    amount = float(policy.get("premium_amount", 0))
    lapse_risk = policy.get("lapse_risk", "low")
    call_count_week = policy.get("call_count_week", 0)

    score = 0

    if days_overdue >= 30:
        score += 100
    elif days_overdue >= 15:
        score += 75
    elif days_overdue >= 7:
        score += 50
    elif days_overdue >= 1:
        score += 25
    else:
        score += 10

    if amount >= 2000:
        score += 30
    elif amount >= 1000:
        score += 20
    elif amount >= 500:
        score += 10

    risk_bonus = {"critical": 25, "high": 15, "medium": 10, "low": 0}
    score += risk_bonus.get(lapse_risk, 0)
    score = max(0, score - (call_count_week * 5))

    if score >= 100:
        label = "critical"
    elif score >= 75:
        label = "high"
    elif score >= 50:
        label = "medium"
    elif score >= 25:
        label = "low"
    else:
        label = "upcoming"

    return score, label


def get_priority_color(label: str) -> str:
    return {
        "critical": "#FF4B4B",
        "high":     "#FF8C00",
        "medium":   "#FFD700",
        "low":      "#00C9A7",
        "upcoming": "#5B8DEF",
    }.get(label, "#888888")


def detect_language(text: str) -> str:
    """Lightweight language detection using Gemini."""
    if not config.GEMINI_API_KEY or not text:
        return "en"
    try:
        result = _call_gemini(
            f"Detect language. Reply ONLY with 2-letter ISO code:\n{text[:200]}",
            max_tokens=5
        )
        return result.lower()[:2]
    except Exception:
        return "en"


def generate_call_script(customer: Dict, policy: Dict) -> str:
    """Generate a dynamic call script for preview before dialing."""
    if not config.GEMINI_API_KEY:
        return _default_script(customer, policy)

    prompt = f"""Write a short, professional, compliant outbound insurance payment reminder call script.

Company: {config.COMPANY_NAME}
Agent: AI Voice Agent
Customer: {customer['full_name']}
Policy Number: {policy['policy_number']}
Policy Type: {policy.get('policy_type', 'Insurance Policy')}
Amount Due: INR {float(policy['premium_amount']):,.2f}
Due Date: {policy['due_date']}
Days Overdue: {policy.get('days_overdue', 0)}

Write only the agent's speaking lines in a clear, numbered script (Opening, Main Message, Handle Objection, Close).
Keep it under 200 words. Be warm, professional, and compliant with TRAI regulations."""

    try:
        return _call_gemini(prompt, max_tokens=400)
    except Exception:
        return _default_script(customer, policy)


def _default_script(customer: Dict, policy: Dict) -> str:
    return f"""1. OPENING:
"Namaste, may I speak with {customer['full_name']}? This is an automated call from {config.COMPANY_NAME} regarding your policy {policy['policy_number']}."

2. MAIN MESSAGE:
"We're reaching out because your premium of INR {float(policy['premium_amount']):,.2f} was due on {policy['due_date']}. To maintain your coverage, please make your payment at the earliest."

3. HANDLE RESPONSE:
"If you have already made the payment, please disregard this message. If you need assistance, please call us at {config.COMPANY_PHONE}."

4. CLOSE:
"Thank you for your time. Have a great day. Dhanyavaad. Goodbye."
"""


def bulk_classify_outcomes(transcripts: List[Dict]) -> List[Dict]:
    """Batch classify multiple call outcomes."""
    results = []
    for item in transcripts:
        classification = classify_outcome(item.get("transcript", ""))
        results.append({
            "call_log_id": item.get("id"),
            **classification
        })
    return results