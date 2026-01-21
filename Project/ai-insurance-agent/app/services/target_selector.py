# app/services/target_selector.py
from datetime import datetime, timedelta, date
from typing import List, Tuple

import pytz
from sqlmodel import Session, select

from app.models import Policy, Customer, CallLog
from app.database import get_session


class TargetSelector:
    """
    Compliance-first target selection for outbound payment collection calls.
    - Only overdue policies
    - No calls within 24 hours
    - Local time 7:00 AM – 10:00 PM IST (relaxed for India testing)
    - Prioritized by days overdue
    """

    # For testing in India – change to stricter hours in production
    CALLING_START_HOUR = 7   # 7:00 AM
    CALLING_END_HOUR = 22    # 10:00 PM (inclusive of 9:59 PM)

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
        local_minute = local_now.minute

        # Debug print
        print(f"Time zone {time_zone}: local time = {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')} "
              f"→ {'ALLOWED' if self.CALLING_START_HOUR <= local_hour < self.CALLING_END_HOUR or 
                   (local_hour == self.CALLING_END_HOUR and local_minute == 0) else 'BLOCKED'}")

        # Allow calls from 7:00 AM to 9:59 PM
        return self.CALLING_START_HOUR <= local_hour < self.CALLING_END_HOUR or \
               (local_hour == self.CALLING_END_HOUR and local_minute == 0)

    def _get_recently_called_customer_ids(self, hours: int = 24) -> set[int]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(Policy.customer_id)
            .join(CallLog, CallLog.policy_id == Policy.id)
            .where(CallLog.timestamp >= cutoff)
        )
        results = self.session.exec(stmt).all()
        return set(results)

    def get_targets(self, limit: int = 50, force_allow: bool = False) -> List[Tuple[str, int, int]]:
        """
        force_allow=True → ignores time window (for testing only!)
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
            if force_allow or self._is_within_calling_window(customer.time_zone):
                days_overdue = policy.calculate_priority_score(today)
                if days_overdue > 0:
                    candidates.append((customer.phone, policy.id, days_overdue))

        candidates.sort(key=lambda x: x[2], reverse=True)

        return candidates[:limit]