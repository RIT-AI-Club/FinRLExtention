"""MCP server for report formatting."""

import json
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from config import claudeConfig
from claude_client import get_claude_client, generate_html
from pdf_converter import html_to_pdf
from prompts import REPORT_PROMPT

logger = logging.getLogger(__name__)
mcp = FastMCP("formatting")

# Reports are written relative to the project root (CWD when launched via mcpservers.yml).
_REPORTS_DIR = Path("reports")


@mcp.tool()
async def format_report(text_blocks: List[str], images: Optional[List[List[str]]], color_scheme: Optional[str] = None, prompt: Optional[str] = None) -> str:
    """
    Formats text and images into a professional HTML/PDF report using an AI model.
    Saves the report to disk and returns a short confirmation with file paths.

    Args:
        text_blocks: A list of text content strings to include in the report.
        images: A list of pairs [base64_data, caption] for chart images.
        color_scheme: Optional color hint for the report theme.
        prompt: Optional custom prompt for the AI model.

    Returns:
        A JSON string with status and output file paths, or a JSON error string.
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
            prompt=prompt,
            reference_image_paths=reference_images,
        )

        # Inject chart images into CHART_PLACEHOLDER_N tokens Claude wrote.
        for i, image_pair in enumerate(user_data.get("images", [])):
            base64_data = image_pair[0]
            caption = image_pair[1] if len(image_pair) > 1 else f"Chart {i + 1}"
            placeholder = f"CHART_PLACEHOLDER_{i}"
            chart_html = (
                f'<div style="width: 794px; margin: 24px 0; break-inside: avoid;">'
                f'<img src="data:image/png;base64,{base64_data}" '
                f'style="width: 650px; height: auto; display: block;">'
                f'<p style="font-size: 11px; color: #888; margin-top: 6px;">'
                f'{caption} · Source: Market data</p>'
                f'</div>'
            )
            if placeholder in report:
                report = report.replace(placeholder, chart_html, 1)
            else:
                logger.warning(f"Placeholder {placeholder} not found in Claude output — chart may be missing")

        # Save HTML and PDF to disk so the chat interface can serve them.
        _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = f"report_{timestamp}"

        html_path = _REPORTS_DIR / f"{stem}.html"
        html_path.write_text(report, encoding="utf-8")
        logger.info(f"HTML saved: {html_path}")

        # Also keep a convenience copy at a fixed path for quick access.
        Path("latest_report.html").write_text(report, encoding="utf-8")

        pdf_path = _REPORTS_DIR / f"{stem}.pdf"
        try:
            await html_to_pdf(report, output_path=str(pdf_path))
            logger.info(f"PDF saved: {pdf_path}")
        except Exception as pdf_err:
            logger.error(f"PDF conversion failed (HTML still saved): {pdf_err}", exc_info=True)
            pdf_path = None

        # Return only status to Gemini — no file paths — so the chat reply stays
        # clean. generate_report.py locates the saved files by scanning the
        # reports directory for the newest entry after the tool call returns.
        result = {
            "status": "success",
            "message": "A comprehensive report has been generated.",
        }
        return json.dumps(result)

    except Exception as e:
        logger.error(f"An unexpected error occurred during report formatting: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to format HTML: {e}"})


if __name__ == "__main__":
    logger.info("Starting formatting MCP server...")
    mcp.run()
