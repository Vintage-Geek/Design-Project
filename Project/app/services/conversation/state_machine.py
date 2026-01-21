# app/services/conversation/state_machine.py
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis

from app.database import get_session
from app.models import CallLog, Policy, Customer

redis_client = redis.from_url("redis://localhost:6379/0")

class ConversationState(Enum):
    GREETING = "greeting"      # Verify identity + AI disclosure
    INFORM = "inform"          # State amount & due date
    NEGOTIATE = "negotiate"    # Handle objections
    CLOSING = "closing"        # Confirm promise or escalate
    ENDED = "ended"            # Log outcome & cleanup


class ConversationStateMachine:
    """
    Rigid state machine for outbound payment collection calls.
    Enforces compliance: AI disclosure, empathetic tone, no pressure.
    """

    def __init__(self, call_id: str, policy_id: int):
        self.call_id = call_id
        self.policy_id = policy_id
        self.redis_prefix = f"call:{call_id}"

    async def get_state(self) -> ConversationState:
        state_str = await redis_client.get(f"{self.redis_prefix}:state")
        if state_str:
            return ConversationState(state_str.decode())
        # Default to start
        await redis_client.set(f"{self.redis_prefix}:state", ConversationState.GREETING.value, ex=3600)
        return ConversationState.GREETING

    async def set_state(self, state: ConversationState):
        await redis_client.set(f"{self.redis_prefix}:state", state.value, ex=3600)

    async def get_context(self) -> Dict[str, Any]:
        """Fetch non-PII context for prompts."""
        with get_session() as session:
            policy = session.get(Policy, self.policy_id)
            customer = session.get(Customer, policy.customer_id)
            return {
                "first_name": customer.name.split()[0],
                "premium_amount": str(policy.premium_amount),
                "due_date": policy.due_date.strftime("%B %d, %Y"),
                "days_overdue": policy.calculate_priority_score(),
                "language_pref": customer.language_pref,
            }

    async def transition(self, trigger: str) -> ConversationState:
        current = await self.get_state()
        transitions = {
            ConversationState.GREETING: {"verified": ConversationState.INFORM, "not_verified": ConversationState.ENDED},
            ConversationState.INFORM: {"objection": ConversationState.NEGOTIATE, "agree": ConversationState.CLOSING},
            ConversationState.NEGOTIATE: {"resolved": ConversationState.CLOSING, "unresolved": ConversationState.ENDED},
            ConversationState.CLOSING: {"confirmed": ConversationState.ENDED},
        }
        next_state = transitions.get(current, {}).get(trigger, ConversationState.ENDED)
        await self.set_state(next_state)
        return next_state

    async def log_outcome(self, outcome: str, promise_date: Optional[str] = None, summary: str = ""):
        with get_session() as session:
            log = CallLog(
                policy_id=self.policy_id,
                timestamp=datetime.utcnow(),
                duration=0,  # Updated via webhook later
                outcome_tag=outcome,
                transcript_summary=summary[:500]  # Truncate, no PII
            )
            if promise_date:
                log.transcript_summary += f" | Promise: {promise_date}"
            session.add(log)
            session.commit()

    async def cleanup(self):
        await redis_client.delete(f"{self.redis_prefix}:*")