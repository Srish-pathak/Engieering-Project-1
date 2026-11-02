"""Helper script: lists the Gemini models your API key can use.  Run:  python test.py"""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("Set GEMINI_API_KEY in your .env file first.")

client = genai.Client(api_key=api_key)
for model in client.models.list():
    print(model.name)
