"""MCP server for report formatting."""

import json
import logging
from typing import List, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from config import claudeConfig
from claude_client import get_claude_client, generate_html
from prompts import REPORT_PROMPT

logger = logging.getLogger(__name__)
mcp = FastMCP("formatting")

@mcp.tool()
async def format_report(text_blocks: List[str], images: Optional[List[List[str]]], color_scheme: Optional[str] = None, prompt: Optional[str] = None) -> str:
    """
    Formats text and images into a professional HTML report using an AI model.

    Args:
        text_blocks: A list of text content strings to include in the report.
        images: A list of tuples, where each tuple contains image data 
                (filename) and its corresponding caption.
        color_scheme: A string containing the main color scheme to format the report.
        prompt: A string containing a custom prompt for the AI model.

    Returns:
        A string containing the generated HTML report, or a JSON error string.
    """
    if not text_blocks:
        error_msg = "No text blocks provided. At least one text block is required."
        logger.warning(error_msg)
        return json.dumps({"error": error_msg})

    try:
        client = get_claude_client()
    except ValueError as e:
        logger.error(f"Failed to initialize Claude client: {e}", exc_info=True)
        return json.dumps({"error": str(e)})

    # Structured cleanly — the old version had duplicate dict keys which
    # silently dropped all but the last value
    user_data = {
        "text_blocks": text_blocks,
        "images": images or [],
    }

    try:
        base_dir = Path(__file__).parent / "reference_images"
        if not base_dir.is_dir():
            logger.warning(f"Reference images directory not found at {base_dir}, proceeding without them.")
            reference_images = []
        else:
            reference_images = [str(p.resolve()) for p in base_dir.iterdir() if p.suffix.lower() == ".png"]
            logger.info(f"Found {len(reference_images)} reference images.")
    except Exception as e:
        logger.error(f"Error loading reference images: {e}", exc_info=True)
        reference_images = []

    try:
        report = await generate_html(
            client=client,
            user_data=user_data,
            system_prompt=REPORT_PROMPT,
            color_scheme=color_scheme,
            prompt=prompt
        )
        with open("latest_report.html", "w", encoding="utf-8") as f:
            f.write(report)
        return report

    except Exception as e:
        logger.error(f"An unexpected error occurred during report formatting: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to format HTML: {e}"})


if __name__ == "__main__":
    logger.info("Starting formatting MCP server...")
    mcp.run()