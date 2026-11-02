"""
IBM Granite Travel Planner — LLM Client
Handles all communication with IBM watsonx.ai using the ibm-watsonx-ai SDK.
"""

import os
from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

load_dotenv()

_client: ModelInference | None = None


def _get_client() -> ModelInference:
    """Lazily initialise and return a singleton ModelInference client."""
    global _client
    if _client is not None:
        return _client

    api_key    = os.getenv("IBM_API_KEY")
    project_id = os.getenv("IBM_PROJECT_ID")
    url        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    model_id   = os.getenv("IBM_GRANITE_MODEL_ID", "ibm/granite-4-h-small")

    if not api_key or api_key == "your_ibm_api_key_here":
        raise EnvironmentError(
            "IBM_API_KEY is not set. Please configure your .env file."
        )
    if not project_id or project_id == "your_ibm_project_id_here":
        raise EnvironmentError(
            "IBM_PROJECT_ID is not set. Please configure your .env file."
        )

    credentials = Credentials(url=url, api_key=api_key)
    _client = ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id,
        params={
            GenParams.MAX_NEW_TOKENS: 1024,
            GenParams.TEMPERATURE:    0.7,
            GenParams.TOP_P:          0.9,
            GenParams.REPETITION_PENALTY: 1.1,
        },
    )
    return _client


SYSTEM_PROMPT = """You are an expert AI Travel Planner powered by IBM Granite. Your job is to help users plan amazing, personalised trips.

You can:
- Suggest destinations based on user preferences, budget, and travel style
- Create detailed day-by-day itineraries
- Recommend accommodation options (budget, mid-range, luxury)
- Suggest transportation modes (flights, trains, buses, car rentals)
- Provide packing tips, visa information, and local customs
- Alert users about weather, safety, or travel advisories
- Optimise schedules to minimise travel time and cost

Always:
- Ask clarifying questions if the user's request is vague
- Structure itineraries clearly with Day 1, Day 2, etc.
- Include estimated costs where possible
- Mention must-see attractions and hidden gems
- Be friendly, enthusiastic, and concise

When responding to itinerary requests, format them with clear headings and bullet points."""


def chat(messages: list[dict]) -> str:
    """
    Send a conversation to IBM Granite and return the assistant reply.

    `messages` is a list of {"role": "user"|"assistant"|"system", "content": str}
    """
    client = _get_client()

    # Build the full prompt using Granite's chat template
    prompt = _build_prompt(messages)
    result  = client.generate_text(prompt=prompt)
    return result.strip()


def _build_prompt(messages: list[dict]) -> str:
    """
    Convert OpenAI-style messages array into a Granite-compatible prompt.
    Granite 3.x uses the standard <|system|> / <|user|> / <|assistant|> tokens.
    """
    parts = [f"<|system|>\n{SYSTEM_PROMPT}\n<|end_of_text|>"]

    for msg in messages:
        role    = msg.get("role", "user")
        content = msg.get("content", "").strip()
        if role == "system":
            continue  # Already injected above
        elif role == "user":
            parts.append(f"<|user|>\n{content}\n<|end_of_text|>")
        elif role == "assistant":
            parts.append(f"<|assistant|>\n{content}\n<|end_of_text|>")

    # Open the final assistant turn for Granite to complete
    parts.append("<|assistant|>")
    return "\n".join(parts)
