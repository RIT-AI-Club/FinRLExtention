"""Gemini API client."""

import yaml
from pathlib import Path
import sys
from google import genai
from google.genai import types
from typing import Any

def load_yaml_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    
config = load_yaml_config()
GOOGLE_API_KEY = config["gemini"]["api_key"]
TEMPERATURE = config["gemini"]["temperature"]
DEFAULT_MODEL = config["gemini"]["model"]
MAX_OUTPUT_TOKENS = config["gemini"]["max_output_tokens"]


def initialize_client():
    """Initialize and return Gemini client."""
    return genai.Client(
        api_key=GOOGLE_API_KEY,
        http_options=types.HttpOptions(api_version='v1beta')
    )


async def generate_html(
    client: genai.Client,
    user_data: dict[str, Any],
    system_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = TEMPERATURE,
    max_output_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    """
    Generate HTML content using Gemini API.
    
    Args:
        client: Initialized Gemini client
        user_data: Dictionary with text_blocks and images
        system_prompt: System instruction for AI
        model: Gemini model to use
        temperature: Generation temperature
    
    Returns:
        Generated HTML string
    
    Raises:
        Exception: If API call fails
    """
    sys.stderr.write("Sending request to Gemini...\n")
    sys.stderr.flush()
    
    response = await client.aio.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text=str(user_data))]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=types.Content(
                parts=[types.Part(text=system_prompt)]
            ),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )
    
    sys.stderr.write("Received response from Gemini\n")
    sys.stderr.flush()
    
    # Extract HTML from response
    html = response.text
    if not html:
        html = "".join(
            part.text
            for part in response.candidates[0].content.parts
            if hasattr(part, "text")
        )
    
    return html
