"""MCP server for report formatting."""

import json
import logging
from typing import List, Tuple
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from config import config
from gemini_client import get_gemini_client, generate_html
from prompts import FORMATTING_PROMPT

# Get a logger for this module
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("formatting")

@mcp.tool()
async def format_report(text_blocks: List[str], images: List[List[str]]) -> str:
    """
    Formats text and images into a professional HTML report using an AI model.
    
    Args:
        text_blocks: A list of text content strings to include in the report.
        images: A list of tuples, where each tuple contains image data 
                (e.g., base64) and its corresponding caption.
    
    Returns:
        A string containing the generated HTML report or a JSON string with an 
        error message if the process fails.
    """
    if not text_blocks:
        error_msg = "No text blocks provided. At least one text block is required."
        logger.warning(error_msg)
        return json.dumps({"error": error_msg})
    
    try:
        # Initialize client, raises ValueError if the key is missing
        client = get_gemini_client()
    except ValueError as e:
        logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
        return json.dumps({"error": str(e)})
    
    # Prepare data structure for the AI
    user_data = {
        "text_blocks": text_blocks,
        "images": images or []
    }

    # Load reference images for style guidance
    try:
        base_dir = Path(__file__).parent / "reference_images"
        if not base_dir.is_dir():
            logger.warning(f"Reference images directory not found at {base_dir}, proceeding without them.")
            reference_images = []
        else:
            reference_images = [
                str(p.resolve()) for p in base_dir.iterdir() 
                if p.suffix.lower() == '.png'
            ]
            logger.info(f"Found {len(reference_images)} reference images.")
    except Exception as e:
        logger.error(f"Error loading reference images: {e}", exc_info=True)
        reference_images = []

    try:
        # Generate HTML content
        html_content = await generate_html(
            client=client, 
            user_data=user_data, 
            system_prompt=FORMATTING_PROMPT, 
            reference_image_paths=reference_images
        )
        
        # Write HTML to a local file for debugging only if enabled in config
        if config.debug:
            debug_path = Path.cwd() / "latest_report.html"
            try:
                debug_path.write_text(html_content, encoding="utf-8")
                logger.info(f"Debug HTML report saved to {debug_path}")
            except IOError as e:
                logger.error(f"Failed to write debug HTML file: {e}")

        return html_content
    
    except Exception as e:
        # This will catch exceptions from generate_html (API errors, parsing errors, etc.)
        logger.error(f"An unexpected error occurred during report formatting: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to format report: {e}"})


if __name__ == "__main__":
    logger.info("Starting formatting MCP server...")
    mcp.run()
    