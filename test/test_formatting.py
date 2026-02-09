from src.backend.mcp_servers.mcp_formatting.server import *
import pytest
import re


def test_html_only():
    pass


@pytest.mark.asyncio
async def test_same_text():
    # Setup: input text
    text_blocks = [
    "Equity Analysis: Apple Inc. (AAPL) Fiscal Performance & Market Position 2024-2026",
    "As of Q1 2026, Apple Inc. maintains a dominant market capitalization, hovering between $3.2T and $3.5T. The primary growth levers have shifted from pure hardware sales to a robust integration of Services and high-margin AI-driven ecosystem features, internally branded as 'Apple Intelligence'.",
    "Historical Price Action: In 2024, AAPL traded in a range of $165 to $198. Following the 2025 breakthrough in edge-computing chips, the stock broke past the $230 resistance level, establishing a new support floor at $215. Currently, technical indicators suggest a bullish consolidation phase.",
    "Revenue Breakdown by Segment (FY 2025):\n* iPhone: 48% (Steady growth in Pro/Ultra models)\n* Services: 26% (All-time high including iCloud+, Music, and Arcade)\n* Wearables & Home: 10%\n* Mac & iPad: 16% (Boosted by the M5 chip transition)",
    "Dividend and Buyback Program: Apple continues its aggressive capital return strategy. In the last four quarters, the company repurchased $90 billion in common stock and increased the quarterly dividend by 4%, signaling strong cash flow confidence despite regulatory pressures in the EU and US.",
    "Strategic Risks: Investors should monitor the ongoing antitrust litigation regarding the App Store's 'walled garden' model. Additionally, supply chain diversification away from specific geographic hubs remains a capital-intensive priority for the 2026-2027 roadmap.",
    "Technical Outlook: The 50-day Moving Average (MA) recently crossed above the 200-day MA, forming a 'Golden Cross' on the weekly chart. RSI levels remain healthy at 58, suggesting room for further upside before hitting overbought territory.",
    "Summary: AAPL remains a cornerstone 'quality' play. Its ability to command premium pricing while expanding its recurring revenue moats through Services makes it a resilient asset in volatile macro environments."
    ]

    images = []

    # Prepare html to be scanned
    def extract_text(html: str) -> str:
        # Remove HTML tags
        no_tags = re.sub(r"<[^>]+>", " ", html)
 
        # Collapse whitespace
        return re.sub(r"\s+", " ", no_tags).strip()
    def tokenize(s: str) -> list[str]:
        # Split on whitespace and punctuation
        return re.findall(r"[A-Za-z0-9]+", s)

    # Invoke: call tool
    html_path = Path("latest_report.html")
    html = html_path.read_text(encoding="utf-8")

    # Extract text from html
    extracted_text = extract_text(html)

    # Tokenize text
    html_tokens = tokenize(extracted_text)

    # Tokenize text blocks
    for block in text_blocks:
        block_tokens = tokenize(block)

        # Assert: make sure each text block appears in HTML unchanged
        index = 0
        for token in block_tokens:
            try:
                index = html_tokens.index(token, index) + 1
            except ValueError:
                raise AssertionError(f"Missing token: {token!r} from block: {block!r}")
