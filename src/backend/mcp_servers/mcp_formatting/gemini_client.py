"""Gemini API client."""

import logging
from pathlib import Path
from google import genai
from google.genai import types
from typing import Any, Optional, List
import json

from config import config

# Get a logger
logger = logging.getLogger(__name__)

def get_gemini_client() -> genai.Client:
    """
    Initialize and return the Gemini client using the configured API key.
    
    Raises:
        ValueError: If the Google API key is not configured.
    """
    if not config.google_api_key or config.google_api_key == "YOUR_API_KEY_HERE":
        logger.error("Google API key is not configured. Please set it in config.yml or as a GOOGLE_API_KEY environment variable.")
        raise ValueError("Google API key is not configured.")
    
    return genai.Client(
        api_key=config.google_api_key,
        http_options=types.HttpOptions(api_version='v1beta') 
    )

def _build_user_prompt_parts(
    user_data: dict[str, Any],
    reference_image_paths: Optional[List[str]] = None
) -> List[types.Part]:
    """Constructs the list of 'parts' for the Gemini API request payload."""
    
    parts = [types.Part(text=f"PRIMARY DATA SOURCE (TRANSCRIPTION ONLY): {json.dumps(user_data)}")]

    if reference_image_paths:
        parts.append(types.Part(text="### VISUAL REFERENCE GALLERY ###"))
        for i, img_path_str in enumerate(reference_image_paths):
            img_path = Path(img_path_str)
            if not img_path.exists():
                logger.warning(f"Reference image not found, skipping: {img_path}")
                continue
            
            logger.info(f"Attaching reference image: {img_path.name}")
            image_bytes = img_path.read_bytes()
            parts.extend([
                types.Part(
                    inline_data=types.Blob(mime_type="image/png", data=image_bytes)
                ),
                types.Part(
                    text=f"REFERENCE IMAGE {i+1}: Analyze the spatial rhythm and layout balance of this image. Use it to inform the 'Couture' editorial vibe of your HTML."
                )
            ])

    parts.append(types.Part(text=(
        "Generate a complete HTML document with embedded CSS for a multi-page A4 PDF financial report using the data and image assets I provide below."
        "Use only the provided data and preserve all values exactly as given (no rounding, no estimating, no invented content). Use all provided chart/image assets as real <img> elements with the exact src values I provide. Do not create placeholders."
        "Design and structure the report as multiple fixed-size A4 pages using .report-page containers, and make sure the content is allocated across pages so each page remains readable and fits within the page. If a page becomes too dense, move content to a new page instead of forcing overflow."
        "Do not use JavaScript. Do not use inline styles. Put all CSS in a single <style> block in the <head>. Return only the final HTML document."
        "This page will ONLY be viewed in pdf format, do NOT design for browser viewing."
    )))
    
    return parts

async def generate_html(
    client: genai.Client,
    user_data: dict[str, Any],
    system_prompt: str,
    reference_image_paths: Optional[List[str]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None
) -> str:
    """
    Generate HTML content using the Gemini API.
    
    Args:
        client: Initialized Gemini client.
        user_data: Dictionary with text_blocks and images.
        system_prompt: System instruction for the AI.
        reference_image_paths: Optional list of paths to reference images.
        model: Gemini model to use (overrides config if provided).
        temperature: Generation temperature (overrides config if provided).
        max_output_tokens: Max output tokens (overrides config if provided).
    
    Returns:
        Generated HTML string.
    
    Raises:
        ValueError: If the API response cannot be parsed.
        Exception: For other API call failures.
    """
    logger.info("Building request for Gemini API.")
    user_parts = _build_user_prompt_parts(user_data, reference_image_paths)

    # Use parameters if provided, otherwise fall back to config values
    final_model = model or config.default_model
    generation_config = types.GenerateContentConfig(
        temperature=temperature if temperature is not None else config.temperature,
        max_output_tokens=max_output_tokens if max_output_tokens is not None else config.max_output_tokens,
        system_instruction=types.Content(parts=[types.Part(text=system_prompt)]),
    )

    logger.info(f"Sending request to Gemini model '{final_model}'...")
    try:
        response = await client.aio.models.generate_content(
            model=final_model,
            contents=[types.Content(role="user", parts=user_parts)],
            config=generation_config,
        )
        logger.info("Received response from Gemini.")
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}", exc_info=True)
        raise

    # Extract HTML from response
    try:
        if response.text:
            return response.text
        # Fallback for cases where the response is structured differently
        return "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))
    except (IndexError, AttributeError, ValueError) as e:
        logger.error(f"Failed to extract text from Gemini response: {e}", exc_info=True)
        logger.debug(f"Full Gemini response object for debugging: {response}")
        raise ValueError("Could not parse HTML from Gemini response.") from e
