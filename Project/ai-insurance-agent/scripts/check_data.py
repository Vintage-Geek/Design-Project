# scripts/check_data.py
import sys
from pathlib import Path

# Automatically add project root to sys.path (makes "from app..." work)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(f"Project root added: {PROJECT_ROOT}")

# ────────────────────────────────────────────────────────────────
# Your original code below
from app.database import get_session
from app.models import Policy, Customer
from sqlmodel import select

print("Checking database contents...\n")

with get_session() as s:
    # Policies
    policies = s.exec(select(Policy)).all()
    print("Policies:")
    if not policies:
        print("  (none found)")
    for p in policies:
        print(f"  ID: {p.id} | Status: {p.status} | Due: {p.due_date} | Customer: {p.customer_id}")

    # Customers
    customers = s.exec(select(Customer)).all()
    print("\nCustomers:")
    if not customers:
        print("  (none found)")
    for c in customers:
        print(f"  ID: {c.id} | Phone: {c.phone} | TZ: {c.time_zone}")