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

@mcp.tool()
async def format_report(text_blocks: List[str], images: Optional[List[List[str]]], color_scheme: Optional[str] = None, prompt: Optional[str] = None, ticker: Optional[str] = None) -> str:
    """
    Formats text and images into a professional HTML report using an AI model,
    and saves the result as a downloadable PDF in the reports/ directory.

    Args:
        text_blocks: A list of text content strings to include in the report.
        images: A list of tuples, where each tuple contains image data
                (filename) and its corresponding caption.
        color_scheme: A string containing the main color scheme to format the report.
        prompt: A string containing a custom prompt for the AI model.
        ticker: Optional stock ticker used to name the saved report file.

    Returns:
        The generated HTML (for the caller's own use), or a JSON error string.
        The report is already saved as a PDF the user can download — do not
        paste this HTML back to the user; just tell them the report is ready.
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

        # Inject real chart images into placeholder tokens Claude wrote.
        # Claude writes CHART_PLACEHOLDER_N tokens; we replace each with a
        # self-contained <img> block carrying the actual base64 data.
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

        with open("latest_report.html", "w", encoding="utf-8") as f:
            f.write(report)

        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{(ticker or 'report').upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pdf_path = reports_dir / f"{stem}.pdf"
        try:
            await html_to_pdf(report, output_path=str(pdf_path))
            logger.info(f"Saved report PDF: {pdf_path}")
        except Exception as e:
            logger.error(f"Failed to save report PDF: {e}", exc_info=True)

        return report

    except Exception as e:
        logger.error(f"An unexpected error occurred during report formatting: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to format HTML: {e}"})


if __name__ == "__main__":
    logger.info("Starting formatting MCP server...")
    mcp.run()