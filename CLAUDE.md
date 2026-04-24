# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

FinRLExtention is a financial equity report generator. It orchestrates three MCP (Model Context Protocol) servers to produce professional HTML/PDF reports for a given stock ticker:
1. Research server fetches financial data via Perplexity API
2. Chart generation server renders price charts via Matplotlib
3. Formatting server generates HTML via Claude API

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Generate a report
python src/backend/generate_report.py AAPL
python src/backend/generate_report.py AAPL --no-pdf
python src/backend/generate_report.py AAPL --advanced-chart --output-dir reports/custom
```

## Running Tests

```bash
# Run all tests (operates on latest_report.html)
pytest test/

# Run a single test
pytest test/test_formatting.py::test_html_only
```

Tests in `test/test_formatting.py` validate the most recently generated report (`latest_report.html`). Run a report generation first if `latest_report.html` is stale.

## Configuration

`config/config.yml` holds all API keys and model settings. This file is git-ignored (see `.gitignore`). Use `config/config.txt` as the template to create it.

`config/mcpservers.yml` defines the three MCP server commands. The MCP client auto-discovers tools from this file at startup.

## Architecture

**Orchestration** — `src/backend/generate_report.py` drives the pipeline:
1. Starts all three MCP servers (via `mcp_client.py`)
2. Calls research tools to gather financial data
3. Fetches real price data via `yfinance`
4. Calls `generate_line_chart` → receives base64 PNG
5. Calls `format_report` → receives HTML with `CHART_PLACEHOLDER_N` tokens
6. Replaces placeholder tokens with actual base64 image data
7. Converts HTML to PDF

**MCP Client** (`src/backend/mcp_client.py`) — Uses Gemini as the orchestrating LLM. Converts MCP tool schemas to Gemini function format (with schema sanitization to strip unsupported fields like `title`, `prefixItems`).

**MCP Servers:**

| Server | Entry Point | API Used | Key Tool |
|--------|------------|----------|----------|
| Research | `mcp_research/server.py` | Perplexity (via OpenAI SDK with custom base_url) | `research_stock`, `research_news`, `research_topic` |
| Chart | `mcp_chart_generation/server.py` | None (Matplotlib) | `generate_line_chart` |
| Formatting | `mcp_formatting/claude_server.py` | Anthropic Claude | `format_report` |

## MCP Server Conventions

- Servers use `FastMCP` with `@mcp.tool()` decorators
- Log to `sys.stderr` (stdout is reserved for MCP transport)
- Return errors as `json.dumps({"error": ...})`
- Config loaded at module level via `config.py`; API clients initialized per-tool-call
- No `__init__.py` in MCP server subdirectories (they use relative imports when run directly)

## Important Implementation Details

- **Chart images**: The formatting server uses `CHART_PLACEHOLDER_N` tokens in its Claude prompt to avoid embedding large base64 strings in LLM context. `generate_report.py` does the substitution after the LLM responds.
- **Matplotlib headless**: `mcp_chart_generation/server.py` calls `matplotlib.use("Agg")` at import time — do not remove this.
- **Retry logic**: The formatting server retries up to 4 times with exponential backoff for Gemini 503 errors.
- **Prompts**: Research prompts live in `mcp_research/prompts.py`; formatting prompts in `mcp_formatting/prompts.py`. These are the primary levers for changing report content and style.
