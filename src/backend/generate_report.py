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
import json
import logging
import os
import random
import shutil
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


def _fetch_real_prices(ticker: str) -> tuple[list[str], list[float]]:
    """Fetch real 90-day closing prices via yfinance."""
    import yfinance as yf
    hist = yf.Ticker(ticker).history(period="3mo")
    if hist.empty:
        raise ValueError(f"No price data returned for {ticker}")
    dates = [d.strftime("%Y-%m-%d") for d in hist.index]
    prices = [round(float(p), 4) for p in hist["Close"].tolist()]
    return dates, prices


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
        stock_result, news_result = await asyncio.gather(
            client.call_tool("research_stock", {"ticker": ticker}),
            client.call_tool("research_news", {"ticker": ticker}),
        )
        text_blocks = [_extract_text(stock_result), _extract_text(news_result)]

        logger.info(f"[1b/4] Supplemental research for: {ticker}")
        sector_result, valuation_result = await asyncio.gather(
            client.call_tool("research_topic", {
                "query": (
                    f"Competitive landscape, industry trends, and market size for the sector "
                    f"that {ticker} operates in. Include key competitors, market share estimates, "
                    f"and any major regulatory or macro factors affecting the industry."
                )
            }),
            client.call_tool("research_topic", {
                "query": (
                    f"Detailed valuation analysis for {ticker}: current P/E, forward P/E, PEG ratio, "
                    f"EV/EBITDA, P/S ratio, comparison to sector peers, and analyst fair value or "
                    f"price target estimates with named analysts or firms."
                )
            }),
        )
        text_blocks.extend([_extract_text(sector_result), _extract_text(valuation_result)])
        logger.info(
            f"Research complete: {len(text_blocks)} blocks, "
            f"{sum(len(b) for b in text_blocks):,} total characters"
        )

        # --- 2. Chart generation ---
        logger.info(f"[2/4] Generating chart for: {ticker}")
        try:
            dates, prices = _fetch_real_prices(ticker)
            chart_caption = f"{ticker.upper()} — 90-Day Closing Price (Real Data)"
            logger.info(f"Fetched {len(dates)} real price points for {ticker}")
        except Exception as e:
            logger.warning(f"yfinance fetch failed ({e}), using dummy prices")
            base = datetime.now()
            dates = [(base - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(90)]
            dates.reverse()
            prices = _dummy_prices(start=150.0, n=90)
            chart_caption = f"{ticker.upper()} — 90-Day Price History"

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
                images.append([item.data, chart_caption])

        # --- 3. Format into HTML ---
        # format_report now saves files to disk and returns a JSON result with paths.
        logger.info("[3/4] Formatting HTML report")
        format_result_text = None
        for attempt in range(4):
            format_result = await client.call_tool(
                "format_report",
                {"text_blocks": text_blocks, "images": images},
            )
            format_result_text = _extract_text(format_result)

            try:
                result_data = json.loads(format_result_text)
            except json.JSONDecodeError:
                raise RuntimeError(f"Formatting server returned unexpected response: {format_result_text[:200]}")

            if result_data.get("status") == "success":
                break

            error_msg = result_data.get("error", format_result_text)
            if "503" not in error_msg and "unavailable" not in error_msg.lower():
                raise RuntimeError(f"Formatting server returned an error: {error_msg}")
            if attempt == 3:
                raise RuntimeError(f"Formatting server failed after 4 attempts: {error_msg}")

            wait = 2 ** attempt
            logger.warning(f"Formatting attempt {attempt + 1}/4 failed, retrying in {wait}s...")
            await asyncio.sleep(wait)

        # format_report already saved the HTML and PDF to disk. Copy them to
        # the caller-specified output_dir so generate_report.py's contract
        # (returning paths under output_dir) still holds.
        logger.info("[4/4] Collecting report files")
        output_paths: dict[str, Path] = {}

        server_html = Path(result_data["html_path"])
        html_path = output_dir / f"{stem}.html"
        if server_html.resolve() != html_path.resolve():
            html_path.write_text(server_html.read_text(encoding="utf-8"), encoding="utf-8")
        output_paths["html"] = html_path
        logger.info(f"HTML at: {html_path}")

        if save_pdf and result_data.get("pdf_path"):
            server_pdf = Path(result_data["pdf_path"])
            pdf_path = output_dir / f"{stem}.pdf"
            if server_pdf.resolve() != pdf_path.resolve():
                shutil.copy2(server_pdf, pdf_path)
            output_paths["pdf"] = pdf_path
            logger.info(f"PDF at: {pdf_path}")
        elif save_pdf:
            # PDF conversion failed inside the server; fall back to local conversion.
            html_content = html_path.read_text(encoding="utf-8")
            pdf_path = output_dir / f"{stem}.pdf"
            await html_to_pdf(html_content, output_path=str(pdf_path))
            output_paths["pdf"] = pdf_path
            logger.info(f"PDF saved (local fallback): {pdf_path}")

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
