"""
PDF conversion utilities using Playwright.
This module provides functionality to convert HTML strings into high-quality PDF documents.
"""

import logging
from playwright.async_api import async_playwright, Error

# Get a logger for this module
logger = logging.getLogger(__name__)

async def html_to_pdf(html_content: str, output_path: str = "report.pdf") -> None:
    """
    Convert an HTML string to a PDF file using Playwright's Chromium engine.
    
    Args:
        html_content: The full HTML content (including CSS) to convert.
        output_path: The file path where the resulting PDF should be saved.
        
    Raises:
        Error: If an error occurs during the Playwright browser operations or PDF generation.
    """
    logger.info(f"Initiating PDF conversion. Output destination: '{output_path}'")
    
    async with async_playwright() as p:
        # Launch Chromium in headless mode
        browser = await p.chromium.launch()
        try:
            # Create a new page instance
            page = await browser.new_page()
            
            # Set the HTML content and wait for it to be loaded
            # A 60-second timeout is used to accommodate complex reports or external fonts
            await page.set_content(html_content, timeout=60000)
            
            # Generate the PDF with pixel-perfect settings for A4 width (794px)
            # We prefer CSS-defined page sizes and backgrounds
            await page.pdf(
                path=output_path,
                width='794px',
                print_background=True,
                prefer_css_page_size=True,
                margin={
                    "top": "0px", 
                    "right": "0px", 
                    "bottom": "0px", 
                    "left": "0px"
                }
            )
            
            logger.info(f"PDF conversion successful: '{output_path}'")
            
        except Error as e:
            logger.error(f"Playwright error during PDF conversion: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during PDF conversion: {e}", exc_info=True)
            raise
        finally:
            # Ensure the browser is closed even if an error occurs
            logger.debug("Closing Playwright browser.")
            await browser.close()
            
