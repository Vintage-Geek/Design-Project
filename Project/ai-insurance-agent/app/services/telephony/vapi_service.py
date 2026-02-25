# app/services/telephony/vapi_service.py
import httpx
from decouple import config
from typing import Optional
from datetime import datetime

VAPI_API_KEY = config("VAPI_API_KEY", default="your-vapi-key-here")
VAPI_BASE_URL = "https://api.vapi.ai"

async def start_outbound_call(phone_number: str, policy_id: int, call_id: str = None) -> Optional[str]:
    """
    Initiate outbound call using Vapi.ai REST API (no SDK required)
    Returns Vapi call ID or None on failure
    """
    if not call_id:
        call_id = f"call_{policy_id}_{int(datetime.utcnow().timestamp())}"

    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "assistantId": config("VAPI_ASSISTANT_ID", default="your-assistant-id"),
        "phoneNumberId": config("VAPI_PHONE_NUMBER_ID", default="your-phone-number-id"),
        "customer": {
            "number": phone_number,
            "name": "Customer"
        },
        "metadata": {
            "policy_id": policy_id,
            "call_source": "ai-insurance-collection",
            "internal_call_id": call_id
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{VAPI_BASE_URL}/call",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            vapi_call_id = data.get("id")
            print(f"[Vapi.ai] Call initiated → vapi_call_id={vapi_call_id}, policy_id={policy_id}")
            return vapi_call_id

        except httpx.HTTPStatusError as e:
            print(f"[Vapi.ai] HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            print(f"[Vapi.ai] Failed to start call for {phone_number}: {e}")
            return None