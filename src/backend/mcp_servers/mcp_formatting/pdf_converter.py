"""PDF conversion utilities."""

from playwright.async_api import async_playwright


async def html_to_pdf(html_content: str, output_path: str = "report.pdf") -> None:
    """
    Convert HTML string to PDF file.
    
    Args:
        html_content: HTML content to convert
        output_path: Path where PDF should be saved
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.set_content(html_content)
            await page.pdf(path=output_path)
        finally:
            await browser.close()
