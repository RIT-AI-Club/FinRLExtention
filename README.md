# FinRLExtention

A financial research assistant that turns a ticker into a designed, print-ready
PDF equity report.

Ask it for a stock in the chat UI and a Gemini-driven agent orchestrates three
MCP servers to answer: Perplexity gathers live research, Matplotlib renders the
price chart, and Claude lays the whole thing out as a self-contained HTML
document that Playwright prints to PDF.

---

## How it works

```
                    ┌──────────────────────────┐
  React UI ────────▶│  FastAPI  (src/backend)  │
  :5173             │        app.py            │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   MCPClient (Gemini)     │  agentic tool-call loop,
                    │      mcp_client.py       │  max 10 iterations
                    └────────────┬─────────────┘
                                 │  stdio
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
     ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
     │   research    │   │    chart_     │   │  formatting   │
     │  Perplexity   │   │  generation   │   │    Claude     │
     │               │   │  Matplotlib   │   │  + Playwright │
     └───────────────┘   └───────────────┘   └───────────────┘
                                                     │
                                              reports/*.pdf
```

Gemini is the orchestrator, not a writer. Its system prompt forbids it from
composing the report itself — a report only exists once `format_report` has
produced one. The three servers are launched as stdio subprocesses from
`config/mcpservers.yml`.

**The chart round-trip is the fiddly part.** Chart PNGs are never sent to
Claude as image data: at ~67K input tokens each they would consume the entire
budget and tempt the model into echoing base64 back. Instead `claude_client.py`
sends only captions and asks Claude to write `CHART_PLACEHOLDER_N` tokens where
charts belong; `claude_server.py` swaps those tokens for real `<img>` tags after
generation. If a placeholder goes missing you'll see a warning in the server log
and a chart-shaped hole in the report.

### MCP tools

| Server | Tool | Purpose |
| --- | --- | --- |
| `research` | `research_stock(ticker)` | Full equity deep-dive — financials, competitive position, technicals, risks. |
| | `research_topic(query)` | General market/finance questions not tied to one ticker. |
| | `research_news(ticker)` | Recent news and sentiment. |
| `chart_generation` | `generate_line_chart(...)` | Closing-price line chart, optional SMA overlay. |
| | `generate_candlestick_chart(...)` | OHLC candlestick chart. |
| `formatting` | `format_report(...)` | Claude writes the HTML; the server injects charts, saves `reports/<TICKER>_<timestamp>.pdf`. |

---

## Prerequisites

- **Python 3.11+** (developed against 3.13) — the numpy 2.x pin sets the floor
- **Node.js & npm** for the frontend
- API keys for **Google Gemini**, **Anthropic Claude**, and **Perplexity**

## Installation

```bash
git clone <repository-url>
cd FinRLExtention
```

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Playwright needs its own browser binary for PDF rendering:

```bash
playwright install chromium
```

Then the frontend:

```bash
cd src/frontend && npm install && cd ../..
```

---

## Configuration

> **There are two config files, not one.** The formatting server runs as a
> separate process with its own working directory and reads a config sitting
> next to its own source. Filling in only the root one leaves the Claude server
> without a key. Both are gitignored.

**1. `config/config.yml`** — read by the orchestrating client and the research
server:

```yaml
gemini:
  api_key: "YOUR_GOOGLE_API_KEY"
  model: "gemini-3.5-flash"
  temperature: 0.7
  max_output_tokens: 8192

perplexity:
  api_key: "YOUR_PERPLEXITY_API_KEY"
  model: "sonar"
  temperature: 0.7
  max_tokens: 4096
```

**2. `src/backend/mcp_servers/mcp_formatting/config.yml`** — read by the
formatting server:

```yaml
claude:
  api_key: "YOUR_ANTHROPIC_API_KEY"
  model: "claude-sonnet-5"
  temperature: 0.7
  max_output_tokens: 50000
```

`ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in the environment take precedence
over the Claude file, so deployments need not write secrets to disk.

### Choosing a Claude model

`claude-sonnet-5` is the default and is a good fit for layout work. Swap in
`claude-opus-5` if report design quality matters more than cost — it is the
stronger model at roughly 2.5× the price. Use the exact IDs above; they carry no
date suffix.

Keep `max_output_tokens` generous. A full HTML report with embedded CSS runs
long, and a low ceiling truncates the document mid-tag.

### Server paths

`config/mcpservers.yml` lists the three servers with paths relative to the
project root, so backend commands must be run from there.

---

## Running

**Backend** — from the project root:

```bash
python -m uvicorn src.backend.app:app --reload --port 8000
```

**Frontend** — in a second terminal:

```bash
cd src/frontend && npm run dev
```

The UI comes up at `http://localhost:5173`. CORS allows that origin by default;
override with the `FRONTEND_ORIGIN` environment variable when deploying.

### Without the UI

`generate_report.py` drives the same pipeline from the command line:

```bash
python src/backend/generate_report.py AAPL
python src/backend/generate_report.py AAPL --advanced-chart
python src/backend/generate_report.py AAPL --no-pdf --output-dir reports/drafts
```

### HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/chat` | `{message, history}` → `{reply, pdf_filename}`. `history` holds prior turns only. |
| `GET` | `/api/reports` | Generated PDFs, newest first. |
| `GET` | `/api/report/download/{filename}` | Download one report. Filenames are resolved and confined to `reports/`. |

---

## Project structure

```
FinRLExtention/
├── config/
│   ├── config.yml          # Gemini + Perplexity keys (gitignored, you create)
│   └── mcpservers.yml      # MCP server launch definitions
├── reports/                # Generated PDFs (gitignored)
├── src/
│   ├── backend/
│   │   ├── app.py              # FastAPI app — chat, list, download
│   │   ├── mcp_client.py       # Gemini orchestrator + tool-call loop
│   │   ├── generate_report.py  # CLI entry point for the same pipeline
│   │   └── mcp_servers/
│   │       ├── mcp_research/          # Perplexity research tools
│   │       ├── mcp_chart_generation/  # Matplotlib charts
│   │       └── mcp_formatting/
│   │           ├── claude_server.py    # format_report tool
│   │           ├── claude_client.py    # prompt assembly, streaming
│   │           ├── prompts.py          # report design system prompt
│   │           ├── pdf_converter.py    # Playwright HTML → PDF
│   │           ├── config.yml          # Claude key (gitignored, you create)
│   │           └── reference_images/   # layout inspiration sent to Claude
│   └── frontend/           # React + Vite chat UI
├── test/
└── requirements.txt
```

---

## Tests

```bash
python -m pytest test/ -q
```

`test/test_formatting.py` validates the most recent generated report — that it is
pure HTML, carries no `<script>` tags or inline event handlers, and contains
valid CSS. It reads `latest_report.html` from the project root and skips when no
report has been generated yet.

---

## Notes and known rough edges

- **Reference images cost tokens.** Every `format_report` call attaches all
  twelve PNGs in `mcp_formatting/reference_images/` as a visual style gallery.
  Thin that directory out to cut per-request cost.
- **Gemini rate limits** are retried five times with exponential backoff. A
  `MALFORMED_FUNCTION_CALL` finish reason is logged and treated as "no tool
  call", which ends the loop rather than crashing.
- **`latest_report.html`** at the project root is overwritten on every report and
  is not tracked.
- The formatting server closes its Anthropic client after each `generate_html`
  call, so a client is constructed per request.
