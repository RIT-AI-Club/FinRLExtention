"""
PDF conversion utilities using Playwright.
This module provides functionality to convert HTML strings into high-quality PDF documents.
"""

import asyncio
import logging
from playwright.sync_api import sync_playwright, Error

logger = logging.getLogger(__name__)


def _html_to_pdf_sync(html_content: str, output_path: str) -> None:
    """
    Synchronous implementation of HTML-to-PDF conversion.
    Runs inside a thread pool via html_to_pdf() to avoid event-loop conflicts.
    """
    logger.info(f"Initiating PDF conversion. Output destination: '{output_path}'")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()

            # Set the HTML content and wait for it to be loaded.
            # A 60-second timeout accommodates complex reports or external fonts.
            page.set_content(html_content, timeout=60000)

            # Generate the PDF with pixel-perfect settings for A4 width (794px).
            # CSS-defined page sizes and backgrounds are preferred.
            page.pdf(
                path=output_path,
                width="794px",
                print_background=True,
                prefer_css_page_size=True,
                margin={
                    "top": "0px",
                    "right": "0px",
                    "bottom": "0px",
                    "left": "0px",
                },
            )

            logger.info(f"PDF conversion successful: '{output_path}'")

        except Error as e:
            logger.error(f"Playwright error during PDF conversion: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during PDF conversion: {e}", exc_info=True)
            raise
        finally:
            logger.debug("Closing Playwright browser.")
            browser.close()


async def html_to_pdf(html_content: str, output_path: str = "report.pdf") -> None:
    """
    Convert an HTML string to a PDF file using Playwright's Chromium engine.

    Runs the synchronous Playwright implementation in a thread pool executor
    to avoid subprocess/event-loop conflicts on Windows (SelectorEventLoop)
    and stay compatible with any ASGI server's loop configuration.

    Args:
        html_content: The full HTML content (including CSS) to convert.
        output_path: The file path where the resulting PDF should be saved.

    Raises:
        Error: If an error occurs during browser operations or PDF generation.
    """
    await asyncio.to_thread(_html_to_pdf_sync, html_content, output_path)