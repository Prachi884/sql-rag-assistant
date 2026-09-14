"""
src/llm_setup.py

Configures the LLM connection (Groq) and exposes a single get_llm() function.

API key resolution order:
    1. Streamlit secrets (production / share.streamlit.io)
    2. .env file (local development)

Keeps API keys and model config in one place.
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load from .env first (for local dev — no-op if file doesn't exist)
load_dotenv()

# If running on Streamlit Cloud, secrets come from st.secrets
# Try to grab it (this block is silently skipped outside Streamlit)
try:
    import streamlit as st
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except (ImportError, AttributeError, FileNotFoundError):
    # Either streamlit isn't installed, or there's no secrets file.
    # That's fine — we'll fall back to .env.
    pass

# Sanity check (clear error if neither source has the key)
if not os.getenv("GROQ_API_KEY"):
    raise ValueError(
        "GROQ_API_KEY not found. Either:\n"
        "  - Local dev: create .env with GROQ_API_KEY=your_key, OR\n"
        "  - Streamlit Cloud: add GROQ_API_KEY in the secrets manager"
    )

# Model config — using the free-tier-friendly model
MODEL_NAME = "llama-3.1-8b-instant"
TEMPERATURE = 0  # 0 = deterministic, best for SQL generation


def get_llm():
    """Return a configured ChatGroq LLM instance."""
    return ChatGroq(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )