
import os
from dotenv import load_dotenv
from groq import (
    Groq,
    AuthenticationError,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
)

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError("GROQ_API_KEY is missing from .env")

model_name ="openai/gpt-oss-120b"
print("Requested model:", model_name)

client = Groq(
    api_key=api_key,
    timeout=30.0,
    max_retries=0,
)

try:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: Groq connection successful.",
            }
        ],
        temperature=0,
        max_completion_tokens=30,
    )

    print("\nAPI key accepted.")
    print("API request successful.")
    if response:
        print(response.choices[0].message.content)
    else:
        print("No response")
    print("Model:", response.model)

except AuthenticationError:
    print("Groq rejected the API key.")
    print("Check the GROQ_API_KEY value in your .env file.")
    raise SystemExit(1)

except RateLimitError:
    print("Groq returned a rate-limit or quota error.")
    print("Check your account's rate limits and usage.")
    raise SystemExit(1)

except APIConnectionError:
    print("Could not connect to Groq.")
    print("Check your internet connection.")
    raise SystemExit(1)

except APIStatusError as exc:
    print(f"Groq returned HTTP status: {exc.status_code}.")
    print("Check the model name, request parameters, and API status.")
    print(f"Error details: {exc.message}")
    raise SystemExit(1)

except Exception as exc:
    print(f"Unexpected error: {type(exc).__name__}: {exc}")
    raise SystemExit(1)
