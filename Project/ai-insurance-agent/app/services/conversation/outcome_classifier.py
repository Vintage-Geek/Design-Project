# app/services/conversation/outcome_classifier.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Optional

class CallOutcome(BaseModel):
    outcome: str = Field(..., description="paid | promise_to_pay | callback_requested | angry_customer | voicemail | other")
    promise_date: Optional[str] = Field(None, description="YYYY-MM-DD if agreed")
    confidence: float = Field(..., ge=0, le=1)

parser = JsonOutputParser(pydantic_object=CallOutcome)

prompt = PromptTemplate.from_template(
    """
    Classify the final call outcome from transcript.
    Rules:
    - "paid" → payment confirmed during call
    - "promise_to_pay" → specific date agreed
    - "callback_requested" → customer asked for later call
    - "angry_customer" → strong negative emotion/threats
    - "voicemail" → no live person
    - "other" → fallback

    Transcript: {transcript}

    Return ONLY valid JSON:
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