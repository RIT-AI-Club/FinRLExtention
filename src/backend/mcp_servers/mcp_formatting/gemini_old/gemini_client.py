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
import asyncio
import json

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
                types.Part(inline_data=types.Blob(mime_type="image/png", data=image_bytes)),
                types.Part(text=f"REFERENCE IMAGE {i+1}: Analyze the spatial rhythm and layout balance of this image. Use it to inform the 'Couture' editorial vibe of your HTML.")
            ])

    # Build an explicit numbered checklist of every image the model MUST include
    images = user_data.get("images", [])
    if images:
        required_imgs = "\n".join(
            f"  {i+1}. <img src=\"{img[0]}\" style=\"width: 650px; height: auto; display: block;\">  <!-- {img[1] if len(img) > 1 else ''} -->"
            for i, img in enumerate(images)
        )
        parts.append(types.Part(text=(
            f"MANDATORY IMAGE CHECKLIST — You MUST embed ALL {len(images)} images below as <img> tags in the final HTML. "
            f"Do not skip, omit, or replace any of them with placeholders. "
            f"Before finishing, count your <img> tags — there must be exactly {len(images)}.\n\n"
            f"Required images (copy src values exactly):\n{required_imgs}"
        )))

    parts.append(types.Part(text=(
        "Generate a complete HTML document with embedded CSS for a multi-page A4 PDF financial report using the data and image assets I provide above.\n"
        "Use only the provided data and preserve all values exactly as given (no rounding, no estimating, no invented content).\n"
        f"CRITICAL: The final HTML must contain exactly {len(images)} <img> tags — one for each image in the mandatory checklist above. Missing even one is a failure.\n"
        "Do not use JavaScript. Put all CSS in a single <style> block in the <head>. Return only the final HTML document.\n"
    )))

    if color_scheme:
        parts.append(types.Part(text=color_scheme))
        parts.append(types.Part(text="Create a color scheme based on the color given. Make the background a slightly lighter, opaque version of the color and make containers a darker opaque version of the color."))
    else:
        parts.append(types.Part(text="Create your own color scheme based on the company given in the data above."))

    return parts

async def generate_html(
    client: genai.Client,
    user_data: dict[str, Any],
    system_prompt: str,
    reference_image_paths: Optional[List[str]] = None,
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
    final_model = "gemini-3.1-flash-lite-preview"
    generation_config = types.GenerateContentConfig(
        temperature=1.0,
        max_output_tokens=max_output_tokens if max_output_tokens is not None else geminiConfig.max_output_tokens,
        system_instruction=system_prompt,
        thinking_config=types.ThinkingConfig(
            thinking_level="medium"  # "low", "medium", or "high"
        )
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
