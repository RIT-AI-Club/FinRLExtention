"""
Claude API client for report generation.
This module handles communication with the Anthropic Claude API, including
constructing prompts with data and reference images.
"""

import asyncio
import base64
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

def _read_reference_image(img_path: Path) -> Optional[bytes]:
    """Blocking read of a reference image, meant to run off the event loop via asyncio.to_thread."""
    if not img_path.exists():
        return None
    return img_path.read_bytes()


async def _build_user_prompt_parts(
    user_data: Dict[str, Any],
    reference_image_paths: Optional[List[str]] = None,
    prompt: Optional[str] = None,
    color_scheme: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Constructs the list of content blocks for the Claude API request payload.

    Args:
        user_data: Dictionary containing text_blocks and images.
        reference_image_paths: Optional list of file paths to styling reference images.
        prompt: Optional custom prompt string to guide the AI's response.
        color_scheme: A string containing the main color scheme for the report.
        
    Returns:
        List[Dict[str, Any]]: A list of content blocks to send to the Claude model.
    """
    # Strip base64 from images — passing raw base64 to Claude wastes ~67K input tokens per
    # image and forces Claude to reproduce the binary in its output, consuming the entire
    # token budget. Instead, pass only captions; the server injects base64 after generation.
    images = user_data.get("images", [])
    user_data_safe = {
        "text_blocks": user_data.get("text_blocks", []),
        "charts": [
            {"index": i, "caption": img[1] if len(img) > 1 else f"Chart {i + 1}"}
            for i, img in enumerate(images)
        ],
    }
    parts = [{"type": "text", "text": f"PRIMARY DATA SOURCE: {json.dumps(user_data_safe)}"}]

    if reference_image_paths:
        parts.append({"type": "text", "text": "### VISUAL REFERENCE GALLERY ###"})
        for i, img_path_str in enumerate(reference_image_paths):
            img_path = Path(img_path_str)
            image_bytes = await asyncio.to_thread(_read_reference_image, img_path)
            if image_bytes is None:
                logger.warning(f"Reference image not found, skipping: {img_path}")
                continue
            logger.info(f"Attaching reference image: {img_path.name}")
            parts.extend([
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(image_bytes).decode(),
                    },
                },
                {"type": "text", "text": f"REFERENCE IMAGE {i+1}: Analyze the spatial rhythm and layout balance of this image. Use it to inform the 'Couture' editorial vibe of your HTML."},
            ])

    # Tell Claude exactly where to place each chart using text tokens.
    # The server replaces these tokens with real <img> tags after generation.
    if images:
        chart_list = "\n".join(
            f"  {i+1}. At the chart position write exactly (nothing else): CHART_PLACEHOLDER_{i}  "
            f"(caption: {images[i][1] if len(images[i]) > 1 else f'Chart {i+1}'})"
            for i in range(len(images))
        )
        parts.append({"type": "text", "text": (
            f"CHART PLACEMENT — The report contains {len(images)} chart(s). "
            f"At each position where a chart should appear, write the EXACT placeholder text shown below "
            f"(no <img> tags, no base64, no other markup — just the raw text). "
            f"The pipeline replaces these tokens with real images after your HTML is complete.\n\n"
            f"{chart_list}"
        )})

    if prompt:
        parts.append({"type": "text", "text": prompt})
    else:
        parts.append({"type": "text", "text": (
            "Generate a complete HTML document with embedded CSS for a multi-page A4 PDF financial report.\n"
            "Use only the provided data; preserve all values exactly (no rounding, estimating, or invented content).\n"
            f"CRITICAL: Insert the text CHART_PLACEHOLDER_0 at the position where the chart should appear "
            f"(e.g. inside the Recent Price Action section). Do NOT write any base64 data or <img> tags yourself.\n"
            "Do not use JavaScript. Put all CSS in a single <style> block in the <head>. Return only the final HTML document.\n"
        )})

    if color_scheme:
        parts.append({"type": "text", "text": color_scheme})
        parts.append({"type": "text", "text": "Create a color scheme based on the color given. Make the background a slightly lighter, opaque version of the color and make containers a darker opaque version of the color. Include any other colors you would like to add but keep it all similar to the color given."})
    else:
        parts.append({"type": "text", "text": "Create your own color scheme based on the company given in the data above."})

    return parts

async def generate_html(
    client: AsyncAnthropic,
    user_data: List[Dict[str, Any]],
    system_prompt: str,
    prompt: Optional[str] = None,
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
        color_scheme: A string containing the main color scheme for the report.
        prompt: A string containing a custom prompt for the AI model.
    Returns:
        str: Generated HTML document string.
    
    Raises:
        ValueError: If the API response cannot be parsed or is empty.
        Exception: For other API call failures.
    """
    logger.info("Building request for Claude API.")

    # Use parameters if provided, otherwise fall back to config values
    final_model = model or claudeConfig.default_model

    logger.info(f"Sending request to Claude model '{final_model}'...")
    try:
        user_parts = await _build_user_prompt_parts(user_data, reference_image_paths, prompt, color_scheme)
        async with client.messages.stream(
            model=final_model,
            messages=[{"role": "user", "content": user_parts}],
            temperature=temperature if temperature is not None else claudeConfig.temperature,
            max_tokens=max_output_tokens if max_output_tokens is not None else claudeConfig.max_output_tokens,
            system=system_prompt
        ) as stream:
            response = ""
            async for text in stream.text_stream:
                response += text
        logger.info("Received response from Claude.")
    except Exception as e:
        logger.error(f"Claude API call failed: {e}", exc_info=True)
        raise
    finally:
        try:
            await client.close()
        except Exception:
            logger.warning("Failed to close Claude client", exc_info=True)

    if not response:
        logger.error("Empty response text from Claude API.")
        raise ValueError("Could not parse HTML from Claude response: empty response text.")

    return response
