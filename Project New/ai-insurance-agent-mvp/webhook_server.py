"""
webhook_server.py

Lightweight FastAPI server to receive VAPI webhooks.
Run alongside Streamlit: uvicorn webhook_server:app --port 8001

Register your webhook URL in VAPI dashboard:
  POST https://your-domain.com/webhook/vapi
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

import database as db
import vapi_client as vapi
import ai_agent as agent
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="InsureCall AI — VAPI Webhook Handler", version="1.0.0")


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify VAPI webhook signature for security."""
    if not config.VAPI_WEBHOOK_SECRET:
        return True  # Skip if not configured
    expected = hmac.new(
        config.VAPI_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@app.post("/webhook/vapi")
async def vapi_webhook(
    request: Request,
    x_vapi_secret: str = Header(None),
):
    body = await request.body()

    if x_vapi_secret and not verify_signature(body, x_vapi_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    msg_type = payload.get("type", "")
    call_data = payload.get("call", {}) or payload
    vapi_call_id = call_data.get("id") or payload.get("id")

    logger.info("VAPI webhook received: type=%s call_id=%s", msg_type, vapi_call_id)

    if msg_type == "end-of-call-report":
        parsed = vapi.parse_webhook_payload(payload)
        transcript = parsed.get("transcript", "")

        classification = {}
        if transcript:
            classification = agent.classify_outcome(transcript)

        update_data = {
            "call_status": "completed",
            "ended_at": datetime.utcnow(),
            "transcript": transcript,
            "summary": parsed.get("summary") or classification.get("summary"),
            "outcome": parsed.get("outcome") or classification.get("outcome"),
            "duration_seconds": parsed.get("duration_seconds"),
            "recording_url": parsed.get("recording_url"),
            "escalation_flag": parsed.get("escalation_flag", False) or classification.get("escalation_flag", False),
            "escalation_reason": parsed.get("escalation_reason") or classification.get("escalation_reason"),
            "language_detected": classification.get("language", "en"),
            "intent_tags": classification.get("intent_tags", []),
            "promise_date": classification.get("promise_date"),
            "promise_amount": classification.get("promise_amount"),
            "callback_dt": classification.get("callback_datetime"),
            "raw_vapi_payload": json.dumps(payload),
        }

        if vapi_call_id:
            db.update_call_log_by_vapi_id(vapi_call_id, {k: v for k, v in update_data.items() if v is not None})
            logger.info("Updated call log for VAPI ID %s with outcome: %s", vapi_call_id, update_data.get("outcome"))

    elif msg_type in ("call-started", "call.started"):
        if vapi_call_id:
            db.update_call_log_by_vapi_id(vapi_call_id, {
                "call_status": "in_progress",
                "answered_at": datetime.utcnow(),
            })

    elif msg_type in ("call-ended", "call.ended"):
        if vapi_call_id:
            db.update_call_log_by_vapi_id(vapi_call_id, {
                "call_status": "ended",
                "ended_at": datetime.utcnow(),
            })

    elif msg_type == "transcript":
        # Real-time transcript chunk — store incrementally
        pass

    elif msg_type == "function-call":
        func_name = payload.get("functionCall", {}).get("name", "")
        if func_name == "escalate_to_human":
            if vapi_call_id:
                db.update_call_log_by_vapi_id(vapi_call_id, {
                    "escalation_flag": True,
                    "escalation_reason": "Triggered by AI during call",
                    "outcome": "escalated",
                })
        return JSONResponse(content={"result": "handled"})

    return JSONResponse(content={"status": "ok", "type": msg_type})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "InsureCall AI Webhook Handler"}


@app.get("/")
async def root():
    return {
        "service": "InsureCall AI",
        "endpoints": {
            "webhook": "POST /webhook/vapi",
            "health": "GET /health",
        }
    }
