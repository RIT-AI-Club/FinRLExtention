from typing import Any
from mcp.server.fastmcp import FastMCP
from google import genai
from google.genai import types
import asyncio
import json
import sys
from playwright.async_api import async_playwright


# Test API Key removed for security
GOOGLE_API_KEY = "AIzaSyAPza0W2UAz15Cdnp154G0a1lX-yNw3sgY" 


# Model instructions to output correctly formatted html (unfinished)
FORMATTING_PROMPT = """
Role: You are a Senior UI/UX Architect and Headless Equity Research Rendering Engine.
Task: Convert raw financial text_blocks and image_data into a high-end, static HTML5 Stock Performance Report optimized for PDF conversion with full background colors.

[VISUAL GUIDELINES]
1. Aesthetic: Minimalist, editorial style (think Apple, Bloomberg, or Financial Times). 
2. Typography: Modern sans-serif stack (system-ui). Fluid typographic scale for headers.
3. Layout: Fixed-width responsive container (max-width: 800px). 
4. PDF & Color Rendering: 
   - CRITICAL: Include `print-color-adjust: exact;` and `-webkit-print-color-adjust: exact;` in the CSS to ensure background colors render in PDF.
   - Use 'page-break-inside: avoid' for figures and data callouts.
   - NO interactive elements (no hover, no sticky).

[BACKGROUND & THEMING]
1. Primary Background: You have the autonomy to choose between a "Dark Terminal" theme (Background: #1a202c, Text: #f7fafc) or a "Premium Light" theme (Background: #fdfdfd, Text: #1a202c).
2. Section Tints: Use subtle background colors for different sections (e.g., a very light emerald tint for "Growth" sections or a soft slate-blue for "Technical Analysis") to create visual separation.
3. Financial Accents: 
   - Bullish/Positive: Emerald Green (#10b981) for backgrounds of positive metric boxes.
   - Bearish/Risk: Crimson Red (#ef4444) for text or borders in risk sections.

[COMPONENTS]
- A high-impact hero header with the stock ticker and a full-width background color.
- Data Tables: Convert lists of numbers into clean tables with alternating row colors (Zebra striping).
- Callout Boxes: Use rounded corners (12px) and soft drop-shadows or contrasting background colors to highlight "Executive Summaries."

[STRICT OPERATIONAL RULES]
- OUTPUT FORMAT: Return ONLY the raw HTML string. 
- FORBIDDEN: Do not include markdown fences (```html), conversational filler, or preamble.
- DATA FIDELITY: Use every text_block and image provided. Do not summarize or alter the wording.

[IMAGE HANDLING]
- Images will be provided as either URLs or base64-encoded data URIs
- If image data is empty or null, gracefully skip that image
- Maintain image aspect ratios and center them within sections

[ERROR RESILIENCE]
- If any data is missing or malformed, continue with available data
- Never output error messages in the HTML itself
- Focus on creating the best possible report with the data provided

[INPUT SCHEMA]
Expect JSON: {"text_blocks": ["str"], "images": [{"data": "url/base64", "caption": "str"}]}
"""

# MCP server creation
mcp = FastMCP("formatting")

async def call_gemini_api(client, user_data, prompt):

    """
    Function that calls the gemini API with the client, user data, and prompt to output its resonse
    
    :param client: Gemini client to call
    :param user_data: Data to be formatted
    :param prompt: Formatting prompt for the AI
    """

    # Available Free Tier Text-Out Models:
    # Gemini 2.5 Flash: models/gemini-2.5-flash
    # Gemini 2.5 Flash Lite: models/gemini-2.5-flash-lite
    # Gemini 3.0 Flash: models/gemini-3.0-flash
    return await client.aio.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text=json.dumps(user_data))]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=types.Content(parts=[types.Part(text=prompt)]),
            temperature=0.7,
        ),
    )


def initialize_client():
    """
    Function to initialize gemini client
    """
    return genai.Client(
        api_key=GOOGLE_API_KEY,
        http_options=types.HttpOptions(api_version='v1beta')
    )

async def html_to_pdf(html_content: str, output_path: str = "report.pdf"):
    """
    Converts raw html string to a pdf file
    
    :param html_content: HTML content to be converted
    :type html_content: str
    :param output_path: Pathname of output pdf
    :type output_path: str
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content)
        await page.pdf(path=output_path)
        await browser.close()

# Initialize MCP Tool
@mcp.tool()
async def format_report(text_blocks: list[str], images: list[Any] ) -> str:

    """
    Collect gathered text and images and format into a professional and creative html only output
    
    :param text_blocks: Input text data to be formatted
    :type text_blocks: list[str]
    :param images: Imput images to be formatted
    :type images: list[Any]
    """

    # Validate inputs
    if not text_blocks:
        return json.dumps({"error": "No text blocks provided"})
    
    if not GOOGLE_API_KEY:
        return json.dumps({"error": "GOOGLE_API_KEY not configured"})

    # Initialize Gemini client
    client = initialize_client()

    # Compile the data into a dictionary
    user_data = {"text_blocks": text_blocks, "images": images}

    sys.stderr.write("Sending request to Gemini...\n")
    sys.stderr.flush()

    # Attempt to call the client
    try:
        # Save response from call
        response = await call_gemini_api(client, user_data, FORMATTING_PROMPT)
        sys.stderr.write("Received response from Gemini\n")

        # Returns the text of the response
        html = response.text
        if not html:
            html = "".join(
                part.text
                for part in response.candidates[0].content.parts
                if hasattr(part, "text")
            )
        return html

    
    # Handles and prints error
    except Exception as e:
        sys.stderr.write(f"Final API Error: {e}\n")
        sys.stderr.flush()
        return json.dumps({"error": str(e)})