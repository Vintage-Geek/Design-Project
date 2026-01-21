# app/services/policy_utils.py
from datetime import date
from sqlmodel import Session, select, update

from app.models import Policy
from app.database import get_session


def mark_overdue_policies(session: Session):
    """Update policy status to 'overdue' if due_date passed and still active."""
    today = date.today()
    stmt = (
        update(Policy)
        .where(
            Policy.due_date < today,
            Policy.status == "active"
        )
        .values(status="overdue")
    )
    session.exec(stmt)
    session.commit()