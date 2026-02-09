"""MCP server for report formatting."""

import json
import sys
from typing import Any
from mcp.server.fastmcp import FastMCP
import yaml
from pathlib import Path

from .gemini_client import initialize_client, generate_html
from .prompts import FORMATTING_PROMPT

def load_yaml_config():
    config_path = Path(__file__).parent / "config.yml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    
config = load_yaml_config()
GOOGLE_API_KEY = config["gemini"]["api_key"]
# Initialize MCP server
mcp = FastMCP("formatting")


@mcp.tool()
async def format_report(text_blocks: list[str], images: list[(str, str)]) -> str:
    """
    Format text and images into a professional HTML report.
    
    Args:
        text_blocks: List of text content to format
        images: List of images with data and captions
    
    Returns:
        Generated HTML string or JSON error message
    """
    # Validate inputs
    if not text_blocks:
        return json.dumps({"error": "No text blocks provided"})
    
    if not GOOGLE_API_KEY:
        return json.dumps({"error": "GOOGLE_API_KEY not configured"})
    
    # Initialize client
    client = initialize_client()
    
    # Prepare data
    user_data = {
        "text_blocks": text_blocks,
        "images": images or []
    }

    # Prepare reference images
    base_dir = Path(__file__).parent / "reference_images"

    reference_images = [
        str(p.resolve()) for p in base_dir.iterdir() 
        if p.suffix.lower() == '.png'
    ]
    
    try:
        # Generate HTML
        html = await generate_html(client, user_data, FORMATTING_PROMPT, reference_images)
        # Write HTML to a local file for debugging
        with open("latest_report.html", "w", encoding="utf-8") as f:
            f.write(html)
        return html
    
    except Exception as e:
        sys.stderr.write(f"API Error: {e}\n")
        sys.stderr.flush()
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
    