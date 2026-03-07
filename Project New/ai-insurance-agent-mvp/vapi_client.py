import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import httpx

from config import config

logger = logging.getLogger(__name__)

HEADERS = {
    "Authorization": f"Bearer {config.VAPI_API_KEY}",
    "Content-Type": "application/json",
}



# ─── Deepgram nova-2 supported language mapping ───────────────────────────────
# Many Indian languages are not natively supported by Deepgram nova-2.
# We fall back to the closest supported language or English (en-IN).
_DEEPGRAM_LANGUAGE_MAP = {
    "en": "en-IN",   # English with Indian accent model
    "hi": "hi",      # Hindi — fully supported
    "ta": "multi",   # Tamil — use multilingual model
    "te": "multi",   # Telugu — use multilingual model
    "bn": "multi",   # Bengali — use multilingual model
    "mr": "multi",   # Marathi — use multilingual model
    "gu": "multi",   # Gujarati — use multilingual model
    "kn": "multi",   # Kannada — use multilingual model
    "ml": "multi",   # Malayalam — use multilingual model
    "pa": "multi",   # Punjabi — use multilingual model
    "zh": "zh",      # Chinese
}

def _map_deepgram_language(lang_code: str) -> str:
    """Map our internal language code to a Deepgram nova-2 supported language."""
    return _DEEPGRAM_LANGUAGE_MAP.get(lang_code, "en-IN")



def _get_first_message(name: str, company: str, pol_num: str, lang: str) -> str:
    """Return language-appropriate opening greeting."""
    greetings = {
        "hi": f"नमस्ते, क्या मैं {name} जी से बात कर सकता हूँ? मैं {company} से बोल रहा हूँ, आपकी पॉलिसी {pol_num} के बारे में।",
        "ta": f"வணக்கம், {name} அவர்களிடம் பேசலாமா? நான் {company} சார்பாக உங்கள் பாலிசி {pol_num} பற்றி அழைக்கிறேன்.",
        "te": f"నమస్కారం, {name} గారితో మాట్లాడవచ్చా? నేను {company} నుండి మీ పాలసీ {pol_num} గురించి కాల్ చేస్తున్నాను.",
        "bn": f"নমস্কার, {name} কি আছেন? আমি {company} থেকে আপনার পলিসি {pol_num} সম্পর্কে কল করছি।",
        "ml": f"നമസ്കാരം, {name} ഉണ്ടോ? ഞാൻ {company} യിൽ നിന്ന് നിങ്ങളുടെ പോളിസി {pol_num} സംബന്ധിച്ച് വിളിക്കുകയാണ്.",
        "gu": f"નમસ્તે, {name} સાહેબ છે? હું {company} તરફથી તમારી પૉલિસી {pol_num} વિશે ફોન કરું છું.",
        "mr": f"नमस्कार, {name} आहेत का? मी {company} कडून तुमच्या पॉलिसी {pol_num} बद्दल फोन करत आहे.",
        "kn": f"ನಮಸ್ಕಾರ, {name} ಇದ್ದಾರಾ? ನಾನು {company} ಯಿಂದ ನಿಮ್ಮ ಪಾಲಿಸಿ {pol_num} ಬಗ್ಗೆ ಕರೆ ಮಾಡುತ್ತಿದ್ದೇನೆ.",
        "pa": f"ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ, {name} ਜੀ ਹਨ? ਮੈਂ {company} ਤੋਂ ਤੁਹਾਡੀ ਪਾਲਿਸੀ {pol_num} ਬਾਰੇ ਫ਼ੋਨ ਕਰ ਰਿਹਾ ਹਾਂ।",
    }
    return greetings.get(
        lang,
        f"Hello, may I speak with {name}? This is a call from {company} regarding your insurance policy {pol_num}."
    )

def _build_assistant_config(customer: Dict, policy: Dict) -> Dict:
    """Build a dynamic VAPI assistant configuration tailored to the customer."""
    lang = customer.get("language_pref", "en")
    lang_name = config.SUPPORTED_LANGUAGES.get(lang, "English")
    days_overdue = policy.get("days_overdue", 0) or 0
    amount = policy.get("premium_amount", 0)
    currency = policy.get("currency", "USD")
    due_str = str(policy.get("due_date", ""))
    pol_num = policy.get("policy_number", "N/A")
    company = config.COMPANY_NAME
    co_phone = config.COMPANY_PHONE

    urgency = "immediately" if days_overdue > 30 else "as soon as possible"
    consequence = (
        "your policy may already be in the grace period and at risk of lapsing"
        if days_overdue > 0
        else "to avoid any lapse in coverage"
    )

    system_prompt = f"""You are a professional, empathetic payment reminder agent for {company}.
Your ONLY purpose is to remind customers about overdue insurance premium payments.

CURRENT CALL CONTEXT:
- Customer name: {customer["full_name"]}
- Policy number: {pol_num}
- Amount due: {currency} {amount:,.2f}
- Original due date: {due_str}
- Days overdue: {days_overdue}
- Language preference: {lang_name}

MISSION:
1. Greet the customer warmly by name.
2. Identify yourself as a representative of {company}.
3. Inform them of the overdue amount ({currency} {amount:,.2f}) and {consequence}.
4. Politely ask if they can make the payment {urgency}.
5. Listen and classify their response:
   - If they've already paid → confirm and thank them.
   - If they promise to pay → get a specific date and amount.
   - If they need a callback → schedule a specific time.
   - If they have questions → answer only about the payment. For disputes or complex issues, offer to transfer to a human agent.
   - If they ask to be removed from calls → confirm their request respectfully.

COMPLIANCE RULES (MANDATORY):
- Always state your name and company at the start.
- Offer an opt-out from automated calls if asked.
- Never threaten, pressure, or use abusive language.
- Never discuss other customers' information.
- Do NOT process payments — direct them to the payment portal at {co_phone}.
- If the customer is distressed or disputes the policy, immediately offer human agent transfer.
- Respect the customer's language preference and respond in {lang_name}.

TONE: Professional, calm, empathetic, compliant.

At the end of the call, always summarize the outcome clearly in English using one of:
OUTCOME: paid | promise_to_pay | callback_requested | unreachable | disputed | escalated | do_not_call
"""

    assistant = {
        "name": f"PaymentAgent_{pol_num}",
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.3,
            "maxTokens": 1000,
            "messages": [{"role": "system", "content": system_prompt}],
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Rachel - supports multilingual
            "language": lang if lang in ("en", "hi") else "en",
            "stability": 0.5,
            "similarityBoost": 0.75,
        },
        "firstMessage": _get_first_message(customer['full_name'], company, pol_num, lang),
        "endCallMessage": f"Thank you for your time. Have a great day. Goodbye.",
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": _map_deepgram_language(lang),
        },
        "recordingEnabled": True,
        "hipaaEnabled": False,
        "silenceTimeoutSeconds": 10,
        "maxDurationSeconds": 600,
        "backgroundSound": "off",
        "endCallPhrases": ["goodbye", "bye", "thank you", "that's all"],
        "metadata": {
            "policy_id": str(policy.get("id", "")),
            "customer_id": str(customer.get("id", "")),
            "policy_number": pol_num,
        },
    }

    if config.HUMAN_AGENT_SIP:
        assistant["forwardingPhoneNumber"] = config.ESCALATION_PHONE

    return assistant


def initiate_call(customer: Dict, policy: Dict) -> Dict[str, Any]:
    """Initiate an outbound call via VAPI."""
    if not config.VAPI_API_KEY:
        return {"success": False, "error": "VAPI_API_KEY not configured", "call_id": None}
    if not config.VAPI_PHONE_NUMBER_ID:
        return {"success": False, "error": "VAPI_PHONE_NUMBER_ID not configured", "call_id": None}

    assistant_config = _build_assistant_config(customer, policy)

    payload = {
        "type": "outboundPhoneCall",
        "phoneNumberId": config.VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": customer["phone"],
            "name": customer["full_name"],
        },
        "assistant": assistant_config,
        "metadata": assistant_config["metadata"],
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{config.VAPI_BASE_URL}/call",
                headers=HEADERS,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "call_id": data.get("id"),
                "status": data.get("status"),
                "raw": data,
            }
    except httpx.HTTPStatusError as e:
        logger.error("VAPI HTTP error: %s %s", e.response.status_code, e.response.text)
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}", "call_id": None}
    except Exception as e:
        logger.exception("VAPI call initiation failed")
        return {"success": False, "error": str(e), "call_id": None}


def get_call_details(vapi_call_id: str) -> Optional[Dict]:
    """Fetch details of an existing call from VAPI."""
    if not config.VAPI_API_KEY:
        return None
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{config.VAPI_BASE_URL}/call/{vapi_call_id}",
                headers=HEADERS,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Failed to fetch VAPI call %s: %s", vapi_call_id, e)
        return None


def list_recent_calls(limit: int = 50) -> list:
    """List recent calls from VAPI."""
    if not config.VAPI_API_KEY:
        return []
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{config.VAPI_BASE_URL}/call",
                headers=HEADERS,
                params={"limit": limit},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        if "getaddrinfo failed" in str(e) or "Name or service not known" in str(e):
            logger.warning("VAPI sync skipped: no network connectivity.")
        else:
            logger.error("Failed to list VAPI calls: %s", e)
        return []


def get_phone_numbers() -> list:
    """List available phone numbers from VAPI."""
    if not config.VAPI_API_KEY:
        return []
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{config.VAPI_BASE_URL}/phone-number", headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


def create_or_update_assistant() -> Optional[str]:
    """Create the payment reminder assistant in VAPI and return its ID."""
    if not config.VAPI_API_KEY:
        return None

    assistant_payload = {
        "name": f"{config.COMPANY_NAME} Payment Reminder Agent",
        "model": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.3,
            "maxTokens": 1000,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "rachel",
        },
        "recordingEnabled": True,
        "silenceTimeoutSeconds": 10,
        "maxDurationSeconds": 600,
    }

    try:
        with httpx.Client(timeout=30) as client:
            if config.VAPI_ASSISTANT_ID:
                resp = client.patch(
                    f"{config.VAPI_BASE_URL}/assistant/{config.VAPI_ASSISTANT_ID}",
                    headers=HEADERS,
                    json=assistant_payload,
                )
            else:
                resp = client.post(
                    f"{config.VAPI_BASE_URL}/assistant",
                    headers=HEADERS,
                    json=assistant_payload,
                )
            resp.raise_for_status()
            return resp.json().get("id")
    except Exception as e:
        logger.error("Failed to create/update assistant: %s", e)
        return None


def parse_webhook_payload(payload: Dict) -> Dict[str, Any]:
    """Parse a VAPI webhook payload into a standardized call result dict."""
    msg_type = payload.get("type", "")
    call_data = payload.get("call", {})
    call_id = call_data.get("id") or payload.get("id")

    result = {
        "vapi_call_id": call_id,
        "call_status": "unknown",
        "outcome": None,
        "transcript": None,
        "summary": None,
        "duration_seconds": None,
        "recording_url": None,
        "language_detected": None,
        "escalation_flag": False,
        "escalation_reason": None,
    }

    if msg_type == "end-of-call-report":
        artifact = payload.get("artifact", {})
        analysis = payload.get("analysis", {})
        result["call_status"] = "completed"
        result["transcript"] = artifact.get("transcript")
        result["summary"] = analysis.get("summary") or payload.get("summary")
        result["recording_url"] = artifact.get("recordingUrl")
        result["duration_seconds"] = int(call_data.get("endedAt", 0) or 0) - int(
            call_data.get("startedAt", 0) or 0
        )
        raw_outcome = (analysis.get("successEvaluation") or "").lower()
        outcome_map = {
            "paid": "paid",
            "promise": "promise_to_pay",
            "callback": "callback_requested",
            "unreachable": "unreachable",
            "voicemail": "voicemail",
            "escalated": "escalated",
            "dispute": "disputed",
        }
        for k, v in outcome_map.items():
            if k in raw_outcome:
                result["outcome"] = v
                break
        if not result["outcome"]:
            result["outcome"] = "unreachable"

        if result["outcome"] in ("escalated", "disputed"):
            result["escalation_flag"] = True
            result["escalation_reason"] = "Customer dispute or complex case"

    elif msg_type in ("call.started", "call-started"):
        result["call_status"] = "in_progress"
    elif msg_type in ("call.ended", "call-ended"):
        result["call_status"] = "ended"

    return result