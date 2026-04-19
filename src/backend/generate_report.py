"""
generate_report.py — Orchestrates the full financial report pipeline.

Usage:
    python src/backend/generate_report.py AAPL
    python src/backend/generate_report.py AAPL --no-pdf
    python src/backend/generate_report.py AAPL --advanced-chart
    python src/backend/generate_report.py AAPL --output-dir reports/custom
"""

import asyncio
import argparse
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure the script always runs relative to the project root so that
# relative MCP server paths in mcpservers.yml resolve correctly.
os.chdir(Path(__file__).parent.parent.parent)
sys.path.insert(0, str(Path(__file__).parent))

from mcp_client import create_mcp_client
from mcp_servers.mcp_formatting.pdf_converter import html_to_pdf

logger = logging.getLogger(__name__)


def _extract_text(result) -> str:
    """Pull all text content from an MCP CallToolResult."""
    return "\n\n".join(
        item.text for item in result.content if hasattr(item, "text")
    )


def _dummy_prices(start: float, n: int, deviation: float = 2.5) -> list[float]:
    """Simple random walk for placeholder price data."""
    prices = [start]
    for _ in range(n - 1):
        prices.append(max(0.01, prices[-1] + random.uniform(-deviation, deviation)))
    return prices


async def generate_report(
    ticker: str,
    save_pdf: bool = True,
    advanced_chart: bool = False,
    output_dir: Path = Path("reports"),
) -> dict[str, Path]:
    """
    Run the full pipeline: research → chart → format → save.

    Args:
        ticker:         Stock ticker symbol, e.g. "AAPL"
        save_pdf:       Whether to also save a PDF alongside the HTML
        advanced_chart: Pass advanced=True to generate_line_chart (adds SMA + annotation)
        output_dir:     Directory to write output files into

    Returns:
        dict with keys "html" and optionally "pdf" mapping to saved file Paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{ticker.upper()}_{timestamp}"

    client = await create_mcp_client()

    try:
        # --- 1. Research ---
        logger.info(f"[1/4] Researching stock: {ticker}")
        stock_result = await client.call_tool("research_stock", {"ticker": ticker})
        news_result = await client.call_tool("research_news", {"ticker": ticker})
        text_blocks = [_extract_text(stock_result), _extract_text(news_result)]

        # --- 2. Chart generation ---
        logger.info(f"[2/4] Generating chart for: {ticker}")
        base = datetime.now()
        dates = [(base - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(90)]
        dates.reverse()
        prices = _dummy_prices(start=150.0, n=90)

        chart_result = await client.call_tool(
            "generate_line_chart",
            {
                "dates": dates,
                "prices": prices,
                "symbol": ticker.upper(),
                "advanced": advanced_chart,
            },
        )

        # ImageContent.data is already base64-encoded by FastMCP
        images = []
        for item in chart_result.content:
            if hasattr(item, "data"):
                images.append([item.data, f"{ticker.upper()} — 90-Day Price History"])

        # --- 3. Format into HTML ---
        logger.info("[3/4] Formatting HTML report")
        format_result = await client.call_tool(
            "format_report",
            {"text_blocks": text_blocks, "images": images},
        )
        html_content = _extract_text(format_result)

        if html_content.strip().startswith('{"error"'):
            raise RuntimeError(f"Formatting server returned an error: {html_content}")

        # --- 4. Save outputs ---
        logger.info("[4/4] Saving report files")
        output_paths: dict[str, Path] = {}

        html_path = output_dir / f"{stem}.html"
        html_path.write_text(html_content, encoding="utf-8")
        output_paths["html"] = html_path
        logger.info(f"HTML saved: {html_path}")

        if save_pdf:
            pdf_path = output_dir / f"{stem}.pdf"
            await html_to_pdf(html_content, output_path=str(pdf_path))
            output_paths["pdf"] = pdf_path
            logger.info(f"PDF saved: {pdf_path}")

        return output_paths

    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a financial report for a stock ticker."
    )
    parser.add_argument("ticker", help="Stock ticker symbol, e.g. AAPL")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")
    parser.add_argument(
        "--advanced-chart",
        action="store_true",
        help="Use advanced chart with SMA overlay and price annotation",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Output directory (default: reports/)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    paths = asyncio.run(
        generate_report(
            ticker=args.ticker,
            save_pdf=not args.no_pdf,
            advanced_chart=args.advanced_chart,
            output_dir=Path(args.output_dir),
        )
    )

    print("\nReport generation complete:")
    for kind, path in paths.items():
        print(f"  {kind.upper()}: {path}")


if __name__ == "__main__":
    main()
