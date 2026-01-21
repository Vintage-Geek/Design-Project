# app/models.py
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlmodel import SQLModel, Field, Column, Date as SQLDate
from sqlalchemy import func, DateTime


class Customer(SQLModel, table=True):
    """Customer table – stores PII with care."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # PII – encrypt at rest in prod
    phone: str = Field(index=True, unique=True)  # PII – primary contact
    language_pref: str = Field(default="en")  # e.g., 'en', 'es'
    time_zone: str = Field(default="UTC")  # IANA tz, e.g., 'America/New_York'


class Policy(SQLModel, table=True):
    """Insurance policy tracking overdue premiums."""
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    premium_amount: Decimal = Field(max_digits=10, decimal_places=2)
    due_date: date = Field(sa_column=Column(SQLDate))
    status: str = Field(default="active")  # active, overdue, paid, canceled

    def calculate_priority_score(self, current_date: Optional[date] = None) -> int:
        """Linear days-overdue score – higher = higher priority."""
        if current_date is None:
            current_date = date.today()
        if self.due_date >= current_date:
            return 0
        return (current_date - self.due_date).days


class CallLog(SQLModel, table=True):
    """Audit trail for every outbound call – required for compliance."""
    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: int = Field(foreign_key="policy.id", index=True)
    timestamp: datetime = Field(
        default_factory=func.now,
        sa_column=Column(DateTime(timezone=True))
    )
    duration: int = Field(default=0)  # seconds
    outcome_tag: str  # e.g., paid, promise_to_pay, callback_requested, angry_customer, voicemail
    recording_url: Optional[str] = Field(default=None)  # secure S3 URL
    transcript_summary: Optional[str] = Field(default=None)  # PII-redacted summary