from image_loader import *
from pdf_converter import *
import asyncio
from test_formatting_server import *

async def main():
    # port = start_image_server(8000)
    # prepare_image_urls(IMAGES)
    with open("latest_report.html", encoding="utf-8") as file:
        content = file.read()
    await html_to_pdf(content)

if __name__ == "__main__":
    asyncio.run(main())