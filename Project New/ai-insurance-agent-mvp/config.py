import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from the same directory as this file
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@localhost:5433/insurance_agent")
    VAPI_API_KEY: str = os.getenv("VAPI_API_KEY", "")
    VAPI_PHONE_NUMBER_ID: str = os.getenv("VAPI_PHONE_NUMBER_ID", "")
    VAPI_ASSISTANT_ID: str = os.getenv("VAPI_ASSISTANT_ID", "")
    VAPI_WEBHOOK_SECRET: str = os.getenv("VAPI_WEBHOOK_SECRET", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ── India-specific settings ──────────────────────────────────────────────
    APP_TIMEZONE: str = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    COUNTRY_CODE: str = "+91"
    CURRENCY: str = "INR"
    CURRENCY_SYMBOL: str = "₹"

    # TRAI (Telecom Regulatory Authority of India) compliance:
    # Automated/pre-recorded calls allowed only 9 AM – 9 PM IST
    # National Do Not Call (NDNC) registry must be respected
    CALL_WINDOW_START: int = int(os.getenv("CALL_WINDOW_START", "9"))
    CALL_WINDOW_END: int = int(os.getenv("CALL_WINDOW_END", "21"))

    # TRAI frequency caps — max 3 calls/day, 7/week per customer
    MAX_CALLS_PER_DAY: int = int(os.getenv("MAX_CALLS_PER_DAY", "3"))
    MAX_CALLS_PER_WEEK: int = int(os.getenv("MAX_CALLS_PER_WEEK", "7"))

    ESCALATION_PHONE: str = os.getenv("ESCALATION_PHONE", "")
    HUMAN_AGENT_SIP: str = os.getenv("HUMAN_AGENT_SIP", "")
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "SecureLife Insurance India")
    COMPANY_PHONE: str = os.getenv("COMPANY_PHONE", "1800-555-0100")
    VAPI_BASE_URL: str = "https://api.vapi.ai"

    # ── Indian languages supported ───────────────────────────────────────────
    SUPPORTED_LANGUAGES: dict = {
        "hi": "Hindi",
        "en": "English",
        "ta": "Tamil",
        "te": "Telugu",
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
    }

    # ── Indian states for dropdown ───────────────────────────────────────────
    INDIAN_STATES: list = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
        "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
        "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
        "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
        "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
        "Uttar Pradesh", "Uttarakhand", "West Bengal",
        "Andaman and Nicobar Islands", "Chandigarh", "Delhi",
        "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
    ]

    # ── Policy types common in India ────────────────────────────────────────
    POLICY_TYPES: list = [
        "Term Life Insurance",
        "Whole Life Insurance",
        "Endowment Plan",
        "ULIP (Unit Linked Insurance Plan)",
        "Health Insurance",
        "Motor Insurance",
        "Home Insurance",
        "Travel Insurance",
        "Personal Accident Insurance",
        "Critical Illness Plan",
        "Pension / Annuity Plan",
        "Micro Insurance",
    ]

    CALL_OUTCOMES: list = [
        "paid",
        "promise_to_pay",
        "callback_requested",
        "unreachable",
        "voicemail",
        "disputed",
        "escalated",
        "do_not_call",
    ]

    PRIORITY_RULES: dict = {
        "critical": {"days_overdue_min": 30, "score": 100},
        "high":     {"days_overdue_min": 15, "score": 75},
        "medium":   {"days_overdue_min": 7,  "score": 50},
        "low":      {"days_overdue_min": 1,  "score": 25},
        "upcoming": {"days_overdue_min": -7, "score": 10},
    }

    # ── TRAI compliance notice text ──────────────────────────────────────────
    TRAI_DISCLAIMER: str = (
        "This is an automated call from {company} regarding your insurance policy. "
        "This call is made in compliance with TRAI regulations. "
        "To be added to our Do Not Call list, press 9 or say 'Do Not Call'."
    )

config = Config()