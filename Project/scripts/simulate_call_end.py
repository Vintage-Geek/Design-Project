# scripts/simulate_call_end.py
from app.services.conversation.outcome_classifier import classify_outcome
import asyncio

async def main():
    transcript = """
    Customer: I can't pay now.
    AI: I understand. Would you promise to pay by 15th January?
    Customer: Yes, on 15th.
    """
    result = await classify_outcome(transcript)
    print(result)

asyncio.run(main())