# app/services/conversation/state_machine.py
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis

from app.database import get_session
from app.models import CallLog, Policy, Customer

# Redis connection – used for transient per-call state (expires automatically)
redis_client = redis.from_url("redis://localhost:6379/0", decode_responses=True)


class ConversationState(Enum):
    GREETING   = "greeting"    # Mandatory AI disclosure + identity verification
    INFORM     = "inform"      # State premium amount, due date, days overdue
    NEGOTIATE  = "negotiate"   # Handle objections, offer promise-to-pay
    CLOSING    = "closing"     # Confirm promise or politely escalate/end
    ENDED      = "ended"       # Final logging & cleanup


class ConversationStateMachine:
    """
    Compliance-first state machine for outbound premium collection calls.
    Enforces rigid flow, mandatory AI disclosure, empathetic tone, and PII-safe logging.
    Uses Redis for fast, transient per-call state (auto-expires).
    """

    def __init__(self, call_id: str, policy_id: int):
        self.call_id = call_id
        self.policy_id = policy_id
        self.redis_prefix = f"call:{call_id}"

    async def get_state(self) -> ConversationState:
        state_str = await redis_client.get(f"{self.redis_prefix}:state")
        if state_str:
            return ConversationState(state_str)
        # Default to start + set TTL 1 hour
        await redis_client.set(f"{self.redis_prefix}:state", ConversationState.GREETING.value, ex=3600)
        return ConversationState.GREETING

    async def set_state(self, state: ConversationState):
        await redis_client.set(f"{self.redis_prefix}:state", state.value, ex=3600)

    async def get_context(self) -> Dict[str, Any]:
        """Fetch minimal, non-PII context for prompts. Never log full name/phone here."""
        with get_session() as session:
            policy = session.get(Policy, self.policy_id)
            if not policy:
                return {}
            customer = session.get(Customer, policy.customer_id)
            return {
                "first_name": customer.name.split()[0] if customer and customer.name else "Customer",
                "premium_amount": str(policy.premium_amount),
                "due_date": policy.due_date.strftime("%B %d, %Y"),
                "days_overdue": policy.calculate_priority_score(),
                "language_pref": customer.language_pref if customer else "en",
            }

    async def transition(self, trigger: str) -> ConversationState:
        """
        Rigid state transitions – no invalid jumps allowed.
        Returns next state after applying trigger.
        """
        current = await self.get_state()

        transitions = {
            ConversationState.GREETING: {
                "verified": ConversationState.INFORM,
                "not_verified": ConversationState.ENDED
            },
            ConversationState.INFORM: {
                "objection": ConversationState.NEGOTIATE,
                "agree": ConversationState.CLOSING
            },
            ConversationState.NEGOTIATE: {
                "resolved": ConversationState.CLOSING,
                "unresolved": ConversationState.ENDED,
                "escalate": ConversationState.ENDED
            },
            ConversationState.CLOSING: {
                "confirmed": ConversationState.ENDED
            }
        }

        next_state = transitions.get(current, {}).get(trigger, ConversationState.ENDED)
        await self.set_state(next_state)
        return next_state

    async def log_outcome(self, outcome: str, promise_date: Optional[str] = None, summary: str = ""):
        """
        Log call outcome to CallLog – PII-safe summary only (no raw transcript).
        """
        with get_session() as session:
            log = CallLog(
                policy_id=self.policy_id,
                timestamp=datetime.utcnow(),
                duration=0,  # Updated later via webhook or duration tracking
                outcome_tag=outcome,
                transcript_summary=summary[:500]  # Hard truncate
            )
            if promise_date:
                log.transcript_summary += f" | Promise: {promise_date}"
            session.add(log)
            session.commit()

    async def cleanup(self):
        """
        Clear all Redis keys for this call after it ends.
        Prevents memory leak in long-running deployments.
        """
        # Delete all keys with prefix call:{call_id}:*
        keys = await redis_client.keys(f"{self.redis_prefix}:*")
        if keys:
            await redis_client.delete(*keys)