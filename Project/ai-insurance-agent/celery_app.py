from celery import Celery

app = Celery('ai_insurance_agent',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0')

@app.task
def select_targets():
    from app.services.target_selector import TargetSelector
    from app.database import get_session
    with get_session() as session:
        selector = TargetSelector(session)
        targets = selector.get_targets(limit=50)
        print(f"Found {len(targets)} targets to dial")
        # TODO: Send to Twilio/Vapi queue