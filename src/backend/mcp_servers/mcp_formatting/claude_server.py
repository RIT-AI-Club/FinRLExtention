"""MCP server for report formatting."""

import json
import logging
from typing import List, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from config import claudeConfig
from claude_client import get_claude_client, generate_html
from prompts import REPORT_PROMPT
from image_loader import start_image_server, prepare_image_urls

# Get a logger for this module
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("formatting")

@mcp.tool()
async def format_report(text_blocks: List[str], images: Optional[List[List[str]]], color_scheme: Optional[str] = None) -> str:
    """
    Formats text and images into a professional HTML report using an AI model.
    
    Args:
        text_blocks: A list of text content strings to include in the report.
        images: A list of tuples, where each tuple contains image data 
                (filename) and its corresponding caption.
        color_scheme: A string containing the main color scheme to format the report.
    
    Returns:
        A string containing the generated HTML report or a JSON string with an 
        error message if the process fails.
    """
    if not text_blocks:
        error_msg = "No text blocks provided. At least one text block is required."
        logger.warning(error_msg)
        return json.dumps({"error": error_msg})
    
    # 1. Start the image server in background (if not already started)
    port = start_image_server(8000)
    
    # 2. Convert filenames to local URLs if necessary
    processed_images = prepare_image_urls(images, port) if port else images
    
    try:
        # Initialize client, raises ValueError if the key is missing
        client = get_claude_client()
    except ValueError as e:
        logger.error(f"Failed to initialize Claude client: {e}", exc_info=True)
        return json.dumps({"error": str(e)})
    
    # Prepare data structure for the AI
    user_data = [{
        "type": "text", "text": text_blocks,
        "type": "text", "text": "Below are image urls.",
        "type": "text", "text": processed_images
    }]

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
        # Generate HTML content using the Gemini client
        report = await generate_html(
            client=client, 
            user_data=user_data, 
            system_prompt=REPORT_PROMPT,
            color_scheme=color_scheme
        )
        
        # Save the latest report for debugging/review purposes
        with open("latest_report.html", "w", encoding="utf-8") as file:
            file.write(report)
            
        return report
    
    except Exception as e:
        # Catch exceptions from generate_html (API errors, parsing errors, etc.)
        logger.error(f"An unexpected error occurred during report formatting: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to format HTML: {e}"})


if __name__ == "__main__":
    logger.info("Starting formatting MCP server...")
    mcp.run()
    