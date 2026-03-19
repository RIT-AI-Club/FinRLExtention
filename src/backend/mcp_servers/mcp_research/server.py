"""MCP server for financial research using Perplexity API."""

import json
import sys

from mcp.server.fastmcp import FastMCP

from config import (
    PERPLEXITY_API_KEY,
    PERPLEXITY_MODEL,
    PERPLEXITY_TEMPERATURE,
    PERPLEXITY_MAX_TOKENS,
)
from perplexity_client import initialize_client, research
from prompts import STOCK_RESEARCH_PROMPT, TOPIC_RESEARCH_PROMPT, NEWS_RESEARCH_PROMPT


# Initialize MCP server
mcp = FastMCP("research")


@mcp.tool()
async def research_stock(ticker: str) -> str:
    """
    Perform comprehensive equity research on a specific stock ticker.
    THIS TOOL SHOULD BE CALLED FIRST when the user asks about a specific stock,
    company, or ticker symbol. Use this for queries like "Research AAPL",
    "Tell me about Tesla", "What do you think about MSFT?", or any request
    for a stock deep-dive. Returns a full research report covering company
    overview, financials, growth prospects, competitive position, technicals,
    analyst consensus, risks/catalysts, and FinRL relevance.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL", "TSLA", "MSFT")

    Returns:
        Comprehensive stock research report or JSON error message
    """
    if not PERPLEXITY_API_KEY:
        return json.dumps({"error": "PERPLEXITY_API_KEY not configured in config/config.yml"})

    client = initialize_client()

    try:
        result = await research(
            client=client,
            system_prompt=STOCK_RESEARCH_PROMPT,
            user_query=f"Provide a comprehensive research report on {ticker.upper()}.",
            model=PERPLEXITY_MODEL,
            temperature=PERPLEXITY_TEMPERATURE,
            max_tokens=PERPLEXITY_MAX_TOKENS,
        )
        return result
    except Exception as e:
        sys.stderr.write(f"API Error: {e}\n")
        sys.stderr.flush()
        return json.dumps({"error": str(e)})


@mcp.tool()
async def research_topic(query: str) -> str:
    """
    Research any financial or market-related topic. Use this for general
    questions that are NOT about a single specific stock ticker. Good for
    queries like "What is the current state of the semiconductor industry?",
    "How do interest rates affect growth stocks?", "Explain the carry trade",
    or follow-up research questions after an initial stock report.

    Args:
        query: The research question or topic to investigate

    Returns:
        Detailed research analysis or JSON error message
    """
    if not PERPLEXITY_API_KEY:
        return json.dumps({"error": "PERPLEXITY_API_KEY not configured in config/config.yml"})

    client = initialize_client()

    try:
        result = await research(
            client=client,
            system_prompt=TOPIC_RESEARCH_PROMPT,
            user_query=query,
            model=PERPLEXITY_MODEL,
            temperature=PERPLEXITY_TEMPERATURE,
            max_tokens=PERPLEXITY_MAX_TOKENS,
        )
        return result
    except Exception as e:
        sys.stderr.write(f"API Error: {e}\n")
        sys.stderr.flush()
        return json.dumps({"error": str(e)})


@mcp.tool()
async def research_news(ticker: str) -> str:
    """
    Get the latest news and sentiment analysis for a specific stock ticker.
    Use this when the user asks about recent news, current events, or sentiment
    for a particular stock. Good for queries like "What's the latest news on TSLA?",
    "Any recent developments for AAPL?", or "What's happening with NVDA this week?".

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL", "TSLA", "MSFT")

    Returns:
        Latest news summary with sentiment analysis or JSON error message
    """
    if not PERPLEXITY_API_KEY:
        return json.dumps({"error": "PERPLEXITY_API_KEY not configured in config/config.yml"})

    client = initialize_client()

    try:
        result = await research(
            client=client,
            system_prompt=NEWS_RESEARCH_PROMPT,
            user_query=f"Provide a comprehensive news summary and sentiment analysis for {ticker.upper()} from the last 7 days.",
            model=PERPLEXITY_MODEL,
            temperature=PERPLEXITY_TEMPERATURE,
            max_tokens=PERPLEXITY_MAX_TOKENS,
        )
        return result
    except Exception as e:
        sys.stderr.write(f"API Error: {e}\n")
        sys.stderr.flush()
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
