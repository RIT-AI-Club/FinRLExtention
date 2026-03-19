"""PDF conversion utilities."""

import logging
from playwright.async_api import async_playwright, Error

# Get a logger
logger = logging.getLogger(__name__)

async def html_to_pdf(html_content: str, output_path: str = "report.pdf") -> None:
    """
    Convert an HTML string to a PDF file using Playwright.
    
    Args:
        html_content: The HTML content to convert.
        output_path: The file path where the PDF should be saved.
        
    Raises:
        Error: If an error occurs during the Playwright process.
    """
    logger.info(f"Starting PDF conversion for output to '{output_path}'...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            # Set a reasonable timeout for content loading
            await page.set_content(html_content, timeout=60000)
            
            # Generate the PDF with specific options for print quality
            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
            )
            logger.info(f"Successfully converted HTML to PDF: '{output_path}'")
            
        except Error as e:
            logger.error(f"An error occurred during PDF conversion: {e}", exc_info=True)
            raise
        finally:
            logger.debug("Closing browser instance.")
            await browser.close()
            
