"""
Gemini API client for report generation.
This module handles communication with the Google Gemini API, including
constructing prompts with data and reference images.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from anthropic import AsyncAnthropic, DefaultAioHttpClient

from config import claudeConfig

# Get a logger for this module
logger = logging.getLogger(__name__)

def get_claude_client() -> AsyncAnthropic:
    """
    Initialize and return the Claude client using the configured API key.
    
    Returns:
        AsyncAnthropic: An initialized Claude API client.
        
    Raises:
        ValueError: If the Cladue API key is not configured or is the default placeholder.
    """
    if not claudeConfig.anthropic_api_key or claudeConfig.anthropic_api_key == "YOUR_API_KEY_HERE":
        logger.error("Anthropic API key is not configured. Please set it in config.yml or as a ANTHROPIC_API_KEY environment variable.")
        raise ValueError("Anthropic API key is not configured.")
    
    return AsyncAnthropic(
        api_key=claudeConfig.anthropic_api_key,
        http_client=DefaultAioHttpClient()
    )

def _build_user_prompt_parts(
    user_data: List[Dict[str, Any]],
    reference_image_paths: Optional[List[str]] = None,
    color_scheme: str = None
) -> List[Dict[str, Any]]:
    """
    Constructs the list of 'parts' for the Claude API request payload.
    
    Args:
        user_data: List of dictionaries containing text blocks and processed image URLs.
        reference_image_paths: Optional list of file paths to styling reference images.
        
    Returns:
        List[Dict[str, Any]]: A list of parts to be sent to the Claude model.
    """
    parts = [{"type": "text", "text": f"PRIMARY DATA SOURCE (TRANSCRIPTION ONLY): {json.dumps(user_data)}"}]

    if reference_image_paths:
        parts.append({"type": "text", "text": "### VISUAL REFERENCE GALLERY ###"})
        for i, img_path_str in enumerate(reference_image_paths):
            img_path = Path(img_path_str)
            if not img_path.exists():
                logger.warning(f"Reference image not found, skipping: {img_path}")
                continue
            
            logger.info(f"Attaching reference image: {img_path.name}")
            image_bytes = img_path.read_bytes()
            parts.extend([
                {"type": "image", "image": image_bytes},
                {"type": "text", "text": f"REFERENCE IMAGE {i+1}: Analyze the spatial rhythm and layout balance of this image. Use it to inform the 'Couture' editorial vibe of your HTML."}
            ])

    parts.append({"type": "text", "text": (
        "Generate a complete HTML document with embedded CSS for a multi-page A4 PDF financial report using the data and image assets I provide above.\n\
        Use only the provided data and preserve all values exactly as given (no rounding, no estimating, no invented content). Use all provided chart/image assets as real <img> elements with the exact src values I provide. Do not create placeholders.\n\
        Do not use JavaScript. Do not use inline styles. Put all CSS in a single <style> block in the <head>. Return only the final HTML document.\n"
    )})

    if color_scheme:
        parts.append({"type": "text", "text": color_scheme})
        parts.append({"type": "text", "text": "Create a color scheme based on the color given. Make the background a slighlty lighter, opaque version of the color and make containers a darker opaque version of the color. Include any other colors you would like to add but keep it all similar to the color given."})
    else: 
        parts.append({"type": "text", "text": "Create your own color scheme based on the company given in the data above."})
    
    return parts

async def generate_html(
    client: AsyncAnthropic,
    user_data: List[Dict[str, Any]],
    system_prompt: str,
    reference_image_paths: Optional[List[str]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    color_scheme: str = None
) -> str:
    """
    Generate HTML content using the Claude API.
    
    Args:
        client: Initialized Claude client.
        user_data: List of dictionaries with text_blocks and images.
        system_prompt: System instruction for the AI.
        reference_image_paths: Optional list of paths to reference images for style.
        model: Claude model to use (overrides config if provided).
        temperature: Generation temperature (overrides config if provided).
        max_output_tokens: Max output tokens (overrides config if provided).
    
    Returns:
        str: Generated HTML document string.
    
    Raises:
        ValueError: If the API response cannot be parsed or is empty.
        Exception: For other API call failures.
    """
    logger.info("Building request for Claude API.")
    user_parts = _build_user_prompt_parts(user_data, reference_image_paths, color_scheme)

    # Use parameters if provided, otherwise fall back to config values
    final_model = model or claudeConfig.default_model

    logger.info(f"Sending request to Claude model '{final_model}'...")
    try:
        async with client.messages.stream(
            model=final_model,
            messages=[{"role": "user", "content": user_parts}],
            temperature=temperature if temperature is not None else claudeConfig.temperature,
            max_tokens=max_output_tokens if max_output_tokens is not None else claudeConfig.max_output_tokens,
            system=system_prompt
        ) as stream:
            response = await stream.get_final_text()
        logger.info("Received response from Claude.")
    except Exception as e:
        logger.error(f"Claude API call failed: {e}", exc_info=True)
        raise
    finally:
        await client.close()

    # Extract HTML from response
    try:
        if response:
            return response
        
        # Fallback for cases where the response is structured differently
        text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, "text")]
        if text_parts:
            return "".join(text_parts)
            
        raise ValueError("Empty response text from Claude API.")
        
    except (IndexError, AttributeError, ValueError) as e:
        logger.error(f"Failed to extract text from Claude response: {e}", exc_info=True)
        logger.debug(f"Full Claude response object for debugging: {response}")
        raise ValueError("Could not parse HTML from Claude response.") from e
