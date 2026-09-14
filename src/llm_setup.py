"""
src/llm_setup.py

Configures the LLM connection (Groq) and exposes a single get_llm() function.
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise ValueError(
        "GROQ_API_KEY not found. Did you create the .env file?"
    )

MODEL_NAME = "openai/gpt-oss-120b"
TEMPERATURE = 0


def get_llm():
    """Return a configured ChatGroq LLM instance."""
    return ChatGroq(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )