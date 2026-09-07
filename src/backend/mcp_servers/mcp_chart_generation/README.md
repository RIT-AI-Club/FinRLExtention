# Chart Generation MCP Server

An MCP server that renders stock charts with Matplotlib and returns them to the
calling model as base64 PNG image content.

## Tools

| Tool | Purpose |
| --- | --- |
| `generate_line_chart(dates, prices, symbol, theme, advanced)` | Closing-price line chart. `advanced=True` overlays a simple moving average whose period is chosen from the time span of the data — 9 for intraday, 20 up to a month, 50 up to ~10 months, 200 beyond. |
| `generate_candlestick_chart(dates, opens, highs, lows, closes, symbol, theme, advanced)` | OHLC candlestick chart. |

Both tools validate their inputs first — mismatched series lengths or
unparseable dates raise before any rendering happens.

## Theming

Every tool takes an optional `theme` dict. Anything you leave out falls back to
`DEFAULT_THEME` in `server.py`; passing `None` for `line` picks a random colour
per chart. See `example_themes.py` for ready-made palettes.

## Running

The server is launched by the orchestrating MCP client via
`config/mcpservers.yml`, using the project's root virtualenv:

```bash
python src/backend/mcp_servers/mcp_chart_generation/server.py
```

It depends only on `matplotlib`, `numpy`, and `fastmcp`, all of which are in the
root `requirements.txt`. The `pyproject.toml` here documents that dependency set
for anyone who wants to run this server standalone.

Matplotlib is forced onto the `Agg` backend before `pyplot` is imported — without
that, the process would try to open a GUI window and crash when run as a
stdio MCP server.

## Manual testing

`test_server.py` exercises both renderers and writes PNGs to
`src/backend/charts/`. The `@mcp.tool()` decorators in `server.py` wrap the
functions for MCP transport, so comment them out if you want to call the
underlying functions directly.
