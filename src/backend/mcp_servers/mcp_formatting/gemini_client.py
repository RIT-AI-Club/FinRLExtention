"""Gemini API client."""

import yaml
from pathlib import Path
import sys
from google import genai
from google.genai import types
from typing import Any
import json

def load_yaml_config():
    config_path = Path(__file__).parent / "config.yml"
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
    reference_image_paths: str = None,
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

    # Turns user data into parts
    user_parts = [types.Part(text=f"PRIMARY DATA SOURCE (TRANSCRIPTION ONLY): {json.dumps(user_data)}")]

    # Add reference images with specific intent
    if reference_image_paths:
        user_parts.append(types.Part(text="### VISUAL REFERENCE GALLERY ###"))
        for i, img_path in enumerate(reference_image_paths):
            path = Path(img_path)
            if path.exists():
                image_bytes = path.read_bytes()
                user_parts.append(
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/png", 
                            data=image_bytes
                        )
                    )
                )
                user_parts.append(
                    types.Part(text=f"REFERENCE IMAGE {i+1}: Analyze the spatial rhythm and layout balance of this image. Use it to inform the 'Couture' editorial vibe of your HTML.")
                )

    # Add a final "Design Directive" at the end of the user parts. 
    user_parts.append(types.Part(text=(
        "DESIGN DIRECTIVE: Synthesize the data above into the visual style inspired by the references. "
        "Prioritize the editorial spacing and geometric sophistication seen in the images. "
        "Optimize HTML output for conversion to a pdf."
        "Do not use default dashboard layouts. Begin HTML generation now."
    )))

    response = await client.aio.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=user_parts
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
