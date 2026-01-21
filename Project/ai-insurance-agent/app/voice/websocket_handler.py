# app/voice/websocket_handler.py
from fastapi import WebSocket, WebSocketDisconnect

async def voice_websocket(websocket: WebSocket, call_id: str, policy_id: int):
    """
    WebSocket endpoint for real-time voice streaming (Twilio/Vapi integration).
    """
    await websocket.accept()
    print(f"WebSocket connected for call {call_id}, policy {policy_id}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from client: {data}")

            # Echo back for testing
            await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for call {call_id}")