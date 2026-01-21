# app/services/conversation/outcome_classifier.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Optional

class CallOutcome(BaseModel):
    outcome: str = Field(..., description="One of: paid, promise_to_pay, callback_requested, angry_customer, voicemail, other")
    promise_date: Optional[str] = Field(None, description="YYYY-MM-DD if explicitly agreed")
    confidence: float = Field(..., ge=0, le=1)

parser = JsonOutputParser(pydantic_object=CallOutcome)

prompt = PromptTemplate.from_template(
    """
    Classify the final outcome from the call transcript.
    Rules:
    - "paid" → only if payment was completed during call
    - "promise_to_pay" → only if specific date was agreed
    - "callback_requested" → customer asked for later call
    - "angry_customer" → strong negative emotion or threats
    - "voicemail" → no live person reached
    - "other" → fallback

    Transcript:
    {transcript}

    Return ONLY valid JSON matching this schema:
    {format_instructions}
    """
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

chain = prompt | llm | parser

async def classify_outcome(transcript: str) -> CallOutcome:
    result = await chain.ainvoke({
        "transcript": transcript,
        "format_instructions": parser.get_format_instructions()
    })
    return CallOutcome(**result)