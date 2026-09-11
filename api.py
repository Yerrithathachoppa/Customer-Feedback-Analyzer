import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client=genai.Client()
app = FastAPI()

# what the caller must SEND us
class Review(BaseModel):
    text: str


#what Gemini gives back , and what we send to the caller.
#We keep it small on purpose -> fewer tokens used.
class Analysis(BaseModel):
    label: str # 'positive','negative',or 'neutral'
    score:int # 1 (very bad) to 5 (very good)
    theme:str # one word: what the review is mainly about (e.g.'delivery')


@app.post("/analysis")
def analysis(review: Review):
    # Retry up to 3 times for transient Gemini errors (503 high demand, 429 rate limit).
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response=client.models.generate_content(
                model='gemini-3.6-flash',
                contents=(
                     "Analyze this customer review.\n"
                    "label must be 'positive', 'negative', or 'neutral'.\n"
                    "score must be an integer from 1 to 5.\n"
                    "theme must be ONE lowercase word for the main topic.\n"
                    "For example: delivery, taste, price, service, quality.\n"
                    f"Review: {review.text}"

                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Analysis
                )
            )
            return response.parsed

        except Exception as e:
            error_msg = str(e)
            # Retry on transient errors (503 high demand, 429 rate limit)
            if ("503" in error_msg or "429" in error_msg or "UNAVAILABLE" in error_msg or "RESOURCE_EXHAUSTED" in error_msg):
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 5s, 10s, 15s
                    print(f"⚠️  Gemini API busy (attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

            # All retries exhausted or non-transient error — return a clean error response.
            print(f"❌ Gemini API error: {error_msg}")
            raise HTTPException(
                status_code=503,
                detail=f"Gemini API error: {error_msg}"
            )

