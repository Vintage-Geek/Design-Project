import os
import google.generativeai as genai
import dotenv

dotenv.load_dotenv(".env")

INSURANCE_PROMPT = """
You are 'Lin', an AI agent for AI Insurance.
Your tone: Empathetic, professional, and helpful.
Goal: Remind customers of overdue premiums. 
- Use 'update_promise' if they give a specific date to pay.
- Use 'escalate' if they are distressed or demand a human.
Rules: Do not threaten. Only inform about policy lapse risks.
"""

def get_agent():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Define Tools for Gemini to call
    def update_promise(policy_id: int, pay_date: str):
        """Schedules a follow-up for a promise to pay."""
        return {"status": "success", "msg": f"Logged PTP for {pay_date}"}

    def escalate():
        """Hands the call off to a human manager."""
        return {"status": "escalating"}

    return genai.GenerativeModel(
        model_name='gemini-2.5-flash-native-audio-dialog',
        system_instruction=INSURANCE_PROMPT,
        tools=[update_promise, escalate]
    )