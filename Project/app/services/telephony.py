import os
import json
import asyncio
import base64
import sys
import audioop_lts   # Required for Python 3.13
from google import generativeai as genai
from dotenv import load_dotenv

sys.modules['audioop'] = audioop_lts  # Workaround for audioop_lts import issues
load_dotenv()

class VoiceStreamManager:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        # Using the exact model from your 2026 quota list
        self.model = genai.GenerativeModel('gemini-2.5-flash-native-audio-dialog')
        
    async def start_stream(self, twilio_ws, stream_sid):
        # Configuration for native audio dialog
        config = {"system_instruction": "You are Lin from 9AI Insurance. Greet the customer warmly and ask about their $250 premium."}

        try:
            async with self.model.live(config=config) as session:
                print("🚀 LIVE SESSION ESTABLISHED")
                
                # Force an initial greeting
                await session.send("Customer joined. Start the conversation as Lin.")

                async def send_to_twilio():
                    async for response in session:
                        if hasattr(response, 'bits') and response.bits:
                            # CONVERSION: Gemini (PCM) -> Twilio (Mulaw)
                            # Phone lines need 8000Hz Mulaw
                            mu_law_audio = audioop_lts.lin2ulaw(response.bits, 2)
                            payload = base64.b64encode(mu_law_audio).decode('utf-8')
                            
                            await twilio_ws.send_json({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": payload}
                            })
                            print("🔈 Lin is speaking...")

                async def receive_from_twilio():
                    async for message in twilio_ws.iter_text():
                        data = json.loads(message)
                        if data['event'] == "media":
                            audio_chunk = base64.b64decode(data['media']['payload'])
                            # CONVERSION: Twilio (Mulaw) -> Gemini (PCM)
                            pcm_audio = audioop.ulaw2lin(audio_chunk, 2)
                            await session.send({"data": pcm_audio, "mime_type": "audio/pcm;rate=8000"})
                        elif data['event'] == "stop":
                            break

                await asyncio.gather(send_to_twilio(), receive_from_twilio())

        except Exception as e:
            print(f"❌ Session Error: {e}")