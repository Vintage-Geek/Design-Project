# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.routers import ingestion
from app.database import get_session
from app.services.conversation.state_machine import ConversationStateMachine, ConversationState
from app.services.conversation.prompts import GREETING_PROMPT, INFORM_PROMPT, NEGOTIATE_PROMPT, CLOSING_PROMPT
from app.services.target_selector import TargetSelector

templates = Jinja2Templates(directory="app/templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup")
    yield
    print("App shutdown")

app = FastAPI(
    title="AI Insurance Payment Collection Agent (Voice)",
    description="Compliant outbound voice AI for overdue premium collection",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.include_router(ingestion.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    with get_session() as session:
        selector = TargetSelector(session)
        targets = selector.get_targets(limit=10)

        from app.models import CallLog
        from sqlmodel import select
        call_logs = session.exec(select(CallLog).order_by(CallLog.timestamp.desc())).limit(10).all()

    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "targets": targets, "call_logs": call_logs}
    )

@app.post("/admin/start-call")
async def start_call(policy_id: int = Form(...)):
    # Placeholder – later replace with real Vapi/Twilio call
    print(f"Manual call triggered for policy {policy_id}")
    return {"message": f"Call initiated for policy {policy_id}"}

# ────────────────────────────────────────────────────────────────
# WebSocket – Real Voice Call Handler
# ────────────────────────────────────────────────────────────────

@app.websocket("/ws/voice/{call_id}/{policy_id}")
async def voice_websocket(websocket: WebSocket, call_id: str, policy_id: int):
    await websocket.accept()
    print(f"[Call Started] call_id={call_id}, policy_id={policy_id}")

    sm = ConversationStateMachine(call_id=call_id, policy_id=policy_id)
    context = await sm.get_context()

    transcript_parts = []

    try:
        # Auto-send greeting on connect
        greeting = GREETING_PROMPT.format(first_name=context.get("first_name", "Customer"))
        await websocket.send_text(greeting)
        print("[AI] Sent greeting")

        while True:
            user_input = await websocket.receive_text()
            print(f"[User] {user_input}")
            transcript_parts.append(user_input)

            current_state = await sm.get_state()
            response = ""

            if current_state == ConversationState.GREETING:
                if any(w in user_input.lower() for w in ["yes", "speaking", "this is", "me"]):
                    await sm.transition("verified")
                    response = "Thank you. Let me share the details.\n\n"
                    response += INFORM_PROMPT.format(**context)
                else:
                    response = "I apologize for the inconvenience. Goodbye."
                    await sm.transition("not_verified")

            elif current_state == ConversationState.INFORM:
                if any(w in user_input.lower() for w in ["pay", "yes", "okay"]):
                    await sm.transition("agree")
                    response = "Great. Would you like to pay now or set a promise date?"
                elif any(w in user_input.lower() for w in ["can't", "no", "later"]):
                    await sm.transition("objection")
                    response = NEGOTIATE_PROMPT.format(user_input=user_input)

            elif current_state == ConversationState.NEGOTIATE:
                if "by" in user_input.lower() and any(c.isdigit() for c in user_input):
                    await sm.transition("resolved")
                    response = "Thank you. Payment date noted."
                else:
                    response = "Please suggest a date within 14 days."

            elif current_state == ConversationState.CLOSING:
                response = "Thank you. Have a great day!"
                await sm.transition("confirmed")

            elif current_state == ConversationState.ENDED:
                break

            if response:
                await websocket.send_text(response)

            if "end call" in user_input.lower():
                break

        # Post-call logging
        transcript = " ".join(transcript_parts)
        outcome = "manual_end"  # Replace with classify_outcome later
        await sm.log_outcome(outcome=outcome, summary=f"Manual end. {transcript[:200]}")
        await sm.cleanup()

    except WebSocketDisconnect:
        print(f"[Disconnected] call_id={call_id}")
        await sm.cleanup()
    except Exception as e:
        print(f"[Error] call_id={call_id}: {e}")
        await sm.cleanup()