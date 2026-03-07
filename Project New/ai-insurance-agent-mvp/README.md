# InsureCall AI — Payment Collection Agent

Automated outbound insurance payment reminder system powered by VAPI (Voice AI), Claude (Conversational AI), PostgreSQL, and Streamlit.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                     │
│  Call Logs │ Overdue Policies │ Customers │ Policies │ Settings │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   database.py    vapi_client.py  ai_agent.py
   (PostgreSQL)   (VAPI calls)   (Claude NLP)
        │              │              │
   call_logs       outbound      classify_outcome
   policies        voice calls   summarize_call
   customers       transcripts   priority_score
        │              │
   scheduler.py   webhook_server.py
   (APScheduler)  (FastAPI - VAPI callbacks)
```

## Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 14+
- VAPI account (https://vapi.ai)
- Anthropic API key

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 4. Initialize database
```bash
# The app auto-initializes tables on first launch
# Or manually: psql -U postgres -c "CREATE DATABASE insurance_agent;"
```

### 5. Run the app
```bash
# Terminal 1: Streamlit UI
streamlit run app.py --server.port 8501

# Terminal 2: VAPI Webhook Handler
uvicorn webhook_server:app --port 8001 --reload
```

### 6. Register VAPI Webhook
In your VAPI dashboard, set webhook URL to:
```
https://your-domain.com/webhook/vapi
```

## File Structure

```
insurance_agent/
├── app.py              # Streamlit UI (all tabs)
├── database.py         # PostgreSQL models + CRUD
├── vapi_client.py      # VAPI API integration
├── ai_agent.py         # Claude NLP + call scripts
├── scheduler.py        # Background job scheduler
├── webhook_server.py   # FastAPI VAPI webhook receiver
├── config.py           # Environment config
├── requirements.txt
└── .env.example
```

## Compliance Features

- ✅ Call window enforcement (configurable hours)
- ✅ Customer consent check before every call
- ✅ Do Not Call (DNC) list support
- ✅ Daily + weekly call frequency caps
- ✅ Multilingual support (8 languages)
- ✅ Full call transcript + audit logging
- ✅ Automated escalation to human agents
- ✅ VAPI webhook signature verification

## VAPI Setup Notes

1. Create a phone number in VAPI dashboard
2. Set `VAPI_PHONE_NUMBER_ID` in `.env`
3. Click "Create / Update VAPI Assistant" in Settings tab
4. Copy the returned assistant ID to `VAPI_ASSISTANT_ID` in `.env`
5. Register webhook URL pointing to your `webhook_server.py`

## Demo Data

On first launch, 8 demo customers and policies are seeded automatically with various overdue/upcoming states for testing.
