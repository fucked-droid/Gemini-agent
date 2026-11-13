
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Check your .env file."
    )

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="Say hello in one sentence."
    )

    print("Gemini response:", repr(response.text))

except Exception as e:
    print("Gemini error:", repr(e))

finally:
    client.close()
