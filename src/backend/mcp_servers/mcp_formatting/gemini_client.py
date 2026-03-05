"""
Gemini API client for report generation.
This module handles communication with the Google Gemini API, including
constructing prompts with data and reference images.
"""

import logging
import json
from pathlib import Path
from typing import Any, Optional, List
from google import genai
from google.genai import types

from config import geminiConfig

# Get a logger for this module
logger = logging.getLogger(__name__)

def get_gemini_client() -> genai.Client:
    """
    Initialize and return the Gemini client using the configured API key.
    
    Returns:
        genai.Client: An initialized Gemini API client.
        
    Raises:
        ValueError: If the Google API key is not configured or is the default placeholder.
    """
    if not geminiConfig.google_api_key or geminiConfig.google_api_key == "YOUR_API_KEY_HERE":
        logger.error("Google API key is not configured. Please set it in config.yml or as a GOOGLE_API_KEY environment variable.")
        raise ValueError("Google API key is not configured.")
    
    return genai.Client(
        api_key=geminiConfig.google_api_key,
        http_options=types.HttpOptions(api_version='v1beta') 
    )

def _build_user_prompt_parts(
    user_data: dict[str, Any],
    reference_image_paths: Optional[List[str]] = None,
    color_scheme: str = None
) -> List[types.Part]:
    """
    Constructs the list of 'parts' for the Gemini API request payload.
    
    Args:
        user_data: Dictionary containing text blocks and processed image URLs.
        reference_image_paths: Optional list of file paths to styling reference images.
        
    Returns:
        List[types.Part]: A list of parts to be sent to the Gemini model.
    """
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
        "Generate a complete HTML document with embedded CSS for a multi-page A4 PDF financial report using the data and image assets I provide above.\n"
        "Use only the provided data and preserve all values exactly as given (no rounding, no estimating, no invented content). Use all provided chart/image assets as real <img> elements with the exact src values I provide. Do not create placeholders.\n"
        "Do not use JavaScript. Do not use inline styles. Put all CSS in a single <style> block in the <head>. Return only the final HTML document.\n"
    )))

    if color_scheme:
        parts.append(types.Part(text=color_scheme))
        parts.append(types.Part(text="Create a color scheme based on the color given. Make the background a slighlty lighter, opaque version of the color and make containers a darker opaque version of the color. Include any other colors you would like to add but keep it all similar to the color given."))
    else: 
        parts.append(types.Part(text="Create your own color scheme based on the company given in the data above."))
    
    return parts

async def generate_html(
    client: genai.Client,
    user_data: dict[str, Any],
    system_prompt: str,
    reference_image_paths: Optional[List[str]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    color_scheme: str = None
) -> str:
    """
    Generate HTML content using the Gemini API.
    
    Args:
        client: Initialized Gemini client.
        user_data: Dictionary with text_blocks and images.
        system_prompt: System instruction for the AI.
        reference_image_paths: Optional list of paths to reference images for style.
        model: Gemini model to use (overrides config if provided).
        temperature: Generation temperature (overrides config if provided).
        max_output_tokens: Max output tokens (overrides config if provided).
    
    Returns:
        str: Generated HTML document string.
    
    Raises:
        ValueError: If the API response cannot be parsed or is empty.
        Exception: For other API call failures.
    """
    logger.info("Building request for Gemini API.")
    user_parts = _build_user_prompt_parts(user_data, reference_image_paths, color_scheme)

    # Use parameters if provided, otherwise fall back to config values
    final_model = model or geminiConfig.default_model
    generation_config = types.GenerateContentConfig(
        temperature=temperature if temperature is not None else geminiConfig.temperature,
        max_output_tokens=max_output_tokens if max_output_tokens is not None else geminiConfig.max_output_tokens,
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
        text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, "text")]
        if text_parts:
            return "".join(text_parts)
            
        raise ValueError("Empty response text from Gemini API.")
        
    except (IndexError, AttributeError, ValueError) as e:
        logger.error(f"Failed to extract text from Gemini response: {e}", exc_info=True)
        logger.debug(f"Full Gemini response object for debugging: {response}")
        raise ValueError("Could not parse HTML from Gemini response.") from e
