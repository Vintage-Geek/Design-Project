# app/services/target_selector.py
from datetime import datetime, timedelta, date
from typing import List, Tuple

import pytz
from sqlmodel import Session, select, and_

from app.models import Policy, Customer, CallLog
from app.database import get_session
from app.services.telephony.vapi_service import start_outbound_call  # NEW IMPORT

class TargetSelector:
    """
    Compliance-first target selection for outbound payment collection calls.
    - Only overdue policies
    - No calls within 24 hours
    - Local time 8:00 AM – 9:00 PM (strict)
    - Prioritized by days overdue
    """

    CALLING_START_HOUR = 8
    CALLING_END_HOUR = 21  # 9:00 PM exclusive

    def __init__(self, session: Session):
        self.session = session

    def _is_within_calling_window(self, time_zone: str) -> bool:
        try:
            tz = pytz.timezone(time_zone)
        except pytz.UnknownTimeZoneError:
            print(f"Invalid time zone: {time_zone} → BLOCKED")
            return False

        local_now = datetime.now(tz)
        local_hour = local_now.hour

        is_allowed = self.CALLING_START_HOUR <= local_hour < self.CALLING_END_HOUR
        print(f"Time zone {time_zone}: local time = {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')} → {'ALLOWED' if is_allowed else 'BLOCKED'}")
        return is_allowed

    def _get_recently_called_customer_ids(self, hours: int = 24) -> set[int]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(Policy.customer_id)
            .join(CallLog, CallLog.policy_id == Policy.id)
            .where(CallLog.timestamp >= cutoff)
        )
        results = self.session.exec(stmt).all()
        return set(results)

    async def get_targets(self, limit: int = 50, auto_dial: bool = False) -> List[Tuple[str, int, int]]:
        """
        Main method: returns eligible targets.
        If auto_dial=True → immediately starts real calls via Vapi.ai
        """
        today = date.today()

        cooldown_customers = self._get_recently_called_customer_ids()

        stmt = (
            select(Policy, Customer)
            .join(Customer, Customer.id == Policy.customer_id)
            .where(Policy.status == "overdue")
        )

        if cooldown_customers:
            stmt = stmt.where(Customer.id.not_in(cooldown_customers))

        results = self.session.exec(stmt).all()

        candidates: List[Tuple[str, int, int]] = []

        for policy, customer in results:
            if not self._is_within_calling_window(customer.time_zone):
                continue

            days_overdue = policy.calculate_priority_score(today)
            if days_overdue <= 0:
                continue

            candidates.append((customer.phone, policy.id, days_overdue))

        candidates.sort(key=lambda x: x[2], reverse=True)
        selected = candidates[:limit]

        # If auto_dial is enabled → start real outbound calls
        if auto_dial:
            for phone, policy_id, _ in selected:
                await start_outbound_call(phone, policy_id)

        return selected