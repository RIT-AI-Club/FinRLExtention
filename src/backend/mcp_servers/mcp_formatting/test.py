
from pdf_converter import *
import asyncio
from test_formatting_server import *

async def main():
    with open("latest_report.html", encoding="utf-8") as file:
        content = file.read()
    await html_to_pdf(content)

if __name__ == "__main__":
    asyncio.run(main())