"""
src/llm_setup.py

Configures the LLM connection (Groq) with automatic model fallback.

Groq frequently rotates their model lineup. This module tries several
production models in priority order and returns the first one that works.

API key resolution order:
    1. Streamlit secrets (production / share.streamlit.io)
    2. .env file (local development)
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load .env first (for local dev)
load_dotenv()

# Try to grab from Streamlit secrets (production)
key_source: str = ".env file"
try:
    import streamlit as st
    secret_key = st.secrets.get("GROQ_API_KEY")
    if secret_key:
        os.environ["GROQ_API_KEY"] = secret_key
        key_source = "Streamlit secrets"
except (ImportError, AttributeError, FileNotFoundError):
    pass

# Sanity check
api_key: str | None = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError(
        "GROQ_API_KEY not found. Either:\n"
        "  - Local dev: create .env with GROQ_API_KEY=your_key, OR\n"
        "  - Streamlit Cloud: add GROQ_API_KEY in the secrets manager"
    )

print(f"[llm_setup] API key loaded from: {key_source}")


# ---------- Model fallback list ----------
# Ordered by likely availability. First one that responds wins.
PRIORITY_MODELS: list[str] = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
    "groq/compound-mini",
]


def _test_model(model_name: str, api_key: str) -> ChatGroq | None:
    """Try a single model with a tiny test prompt. Returns the LLM or None."""
    try:
        llm = ChatGroq(
            model=model_name,
            temperature=0,
            groq_api_key=api_key,
            timeout=10,
        )
        # Tiny ping to confirm it works
        _ = llm.invoke("hi").content
        return llm
    except Exception as e:
        print(f"[llm_setup] {model_name} unavailable: {type(e).__name__}")
        return None


def get_llm() -> ChatGroq:
    """
    Return a configured ChatGroq LLM instance.
    Tries multiple models in priority order; returns the first that responds.
    """
    for model_name in PRIORITY_MODELS:
        llm = _test_model(model_name, api_key)
        if llm is not None:
            print(f"[llm_setup] Active model: {model_name}")
            return llm

    raise RuntimeError(
        "No Groq models are accessible with this API key. "
        "Check your key at https://console.groq.com"
    )