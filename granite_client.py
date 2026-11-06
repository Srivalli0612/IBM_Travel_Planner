"""
IBM Granite Travel Planner — LLM Client (HTTP version)
Uses direct REST API calls instead of ibm-watsonx-ai SDK.
This avoids pandas/pillow/numpy build issues on Streamlit Cloud.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Try to load from Streamlit secrets if available
try:
    import streamlit as st
    _secrets = st.secrets
except Exception:
    _secrets = {}

def _get_env(key: str) -> str:
    """Get value from Streamlit secrets first, then .env"""
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, "")


_iam_token: str = ""
_iam_token_expiry: float = 0.0


def _get_iam_token() -> str:
    """Get or refresh IBM IAM Bearer token."""
    global _iam_token, _iam_token_expiry
    import time

    if _iam_token and time.time() < _iam_token_expiry - 60:
        return _iam_token

    api_key = _get_env("IBM_API_KEY")
    if not api_key or api_key == "your_ibm_api_key_here":
        raise EnvironmentError(
            "IBM_API_KEY is not set. Please configure your Streamlit secrets or .env file."
        )

    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "grant_type":    "urn:ibm:params:oauth:grant-type:apikey",
            "apikey":        api_key,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _iam_token        = data["access_token"]
    _iam_token_expiry = time.time() + data.get("expires_in", 3600)
    return _iam_token


SYSTEM_PROMPT = """You are an expert AI Travel Planner powered by IBM Granite. Your job is to help users plan amazing, personalised trips.

You can:
- Suggest destinations based on user preferences, budget, and travel style
- Create detailed day-by-day itineraries
- Recommend accommodation options (budget, mid-range, luxury)
- Suggest transportation modes (flights, trains, buses, car rentals)
- Provide packing tips, visa information, and local customs
- Provide weather-aware travel advice
- Estimate trip budgets and costs

Always:
- Ask clarifying questions if the user's request is vague
- Structure itineraries clearly with Day 1, Day 2, etc.
- Include estimated costs where possible
- Mention must-see attractions and hidden gems
- Be friendly, enthusiastic, and concise"""


def _build_prompt(messages: list) -> str:
    """
    Convert messages list into a plain prompt for granite-4-h-small.
    This model uses a simple Human/Assistant format without special tokens.
    """
    # Start with system instructions as a plain prefix
    parts = [SYSTEM_PROMPT, ""]

    for msg in messages:
        role    = msg.get("role", "user")
        content = msg.get("content", "").strip()
        if role == "system":
            continue
        elif role == "user":
            parts.append(f"Human: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")

    # Open the assistant turn
    parts.append("Assistant:")
    return "\n".join(parts)


def chat(messages: list) -> str:
    """Send conversation to IBM Granite via REST API and return reply."""
    token      = _get_iam_token()
    url        = _get_env("IBM_WATSONX_URL") or "https://us-south.ml.cloud.ibm.com"
    project_id = _get_env("IBM_PROJECT_ID")
    model_id   = _get_env("IBM_GRANITE_MODEL_ID") or "ibm/granite-4-h-small"

    if not project_id or project_id == "your_ibm_project_id_here":
        raise EnvironmentError(
            "IBM_PROJECT_ID is not set. Please configure your Streamlit secrets or .env file."
        )

    endpoint = f"{url.rstrip('/')}/ml/v1/text/generation?version=2023-05-29"
    payload  = {
        "model_id":   model_id,
        "project_id": project_id,
        "input":      _build_prompt(messages),
        "parameters": {
            "max_new_tokens":     1024,
            "temperature":        0.7,
            "top_p":              0.9,
            "repetition_penalty": 1.1,
            "stop_sequences":     ["Human:", "\nHuman:"],
        },
    }

    resp = requests.post(
        endpoint,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        timeout=60,
    )

    if resp.status_code == 404:
        detail = resp.json()
        raise EnvironmentError(f"Cannot set Project or Space\nReason: {resp.text}")
    if resp.status_code == 403:
        detail = resp.json()
        errors = detail.get("errors", [{}])
        raise EnvironmentError(f"LLM error: {errors[0].get('message', resp.text)}")

    resp.raise_for_status()
    result = resp.json()
    return result["results"][0]["generated_text"].strip()
