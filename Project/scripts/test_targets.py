# scripts/test_targets.py
import sys
from pathlib import Path

# Make sure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(f"Project root added to sys.path: {PROJECT_ROOT}")

from app.services.target_selector import TargetSelector
from app.database import get_session

print("Testing TargetSelector...")

with get_session() as session:
    selector = TargetSelector(session)
    targets = selector.get_targets(limit=10)

    if not targets:
        print("No eligible targets found at this time.")
        print("Possible reasons:")
        print("  - No policies with status='overdue'")
        print("  - Current local time outside 8:00 AM – 9:00 PM in customer's time zone")
        print("  - Customers were called in the last 24 hours")
    else:
        print(f"Found {len(targets)} eligible target(s):")
        for phone, policy_id, score in targets:
            print(f"  Phone: {phone} | Policy ID: {policy_id} | {score} days overdue")