import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv(".env")

# Initialize Twilio Client
client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

# Your personal phone number (include + and country code, e.g., +91...)
MY_PERSONAL_PHONE = "+917373077820" 

def trigger_call():
    print(f"Requesting Twilio to call {MY_PERSONAL_PHONE}...")
    
    full_url = f"{os.getenv('PUBLIC_SERVER_URL')}/voice/incoming"
    print(f"DEBUG: Twilio is trying to reach: {full_url}")

    call = client.calls.create(
        to=MY_PERSONAL_PHONE,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        url=full_url
    )

    # This triggers the call. When you answer, Twilio hits your 'url' 
    # which points to your ngrok logic.
    call = client.calls.create(
        to=MY_PERSONAL_PHONE,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        url=f"{os.getenv('PUBLIC_SERVER_URL')}/voice/incoming"
    )
    
    print(f"Call Sid: {call.sid}")
    print("Your phone should ring in a few seconds!")

if __name__ == "__main__":
    trigger_call()