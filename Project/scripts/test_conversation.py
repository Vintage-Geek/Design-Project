# scripts/test_conversation.py
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.conversation.state_machine import ConversationStateMachine, ConversationState

async def test_state_machine():
    # Simulate a call
    sm = ConversationStateMachine(call_id="test_call_123", policy_id=1)

    print(f"Initial state: {await sm.get_state()}")

    # Simulate user verification
    await sm.transition("verified")
    print(f"After verification: {await sm.get_state()}")

    # Simulate objection
    await sm.transition("objection")
    print(f"After objection: {await sm.get_state()}")

    # Simulate resolution
    await sm.transition("resolved")
    print(f"After resolution: {await sm.get_state()}")

    # Simulate confirmation
    await sm.transition("confirmed")
    print(f"Final state: {await sm.get_state()}")

    await sm.cleanup()

import asyncio
asyncio.run(test_state_machine())

from app.services.conversation.prompts import GREETING_PROMPT

context = {"first_name": "Senthoor"}
print(GREETING_PROMPT.format(**context))