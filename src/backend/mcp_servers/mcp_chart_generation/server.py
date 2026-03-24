"""
MCP server for chart generation
"""

import matplotlib
# CRITICAL: Set the backend to "Agg" before importing pyplot.
# This prevents the server from trying to open a GUI window, which would crash it.
matplotlib.use("Agg")
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from chart_helper_functions import *

# Default theme for graph
DEFAULT_THEME = {
    "line": None,                     # if None, a random color from COLORS will be used
    "text": "dimgrey",                 # axis labels, tick labels, title
    "grid": "#cccccc",                  # grid line color
    "background": "white",              # axes background color
    "figure_background": "none",        # figure background (set via alpha=0 in your code)
    "trend_line": "gold",                # SMA line color (advanced chart)
    "trend_line_style": "--",            # SMA line style
    "annotation_background": "yellow",   # annotation box fill
    "annotation_edge": "black",          # annotation box edge
    "annotation_text": "black",          # annotation text color
    "marker": ".",                       # line marker style
    "line_width": 2,                      # main line width
}

# Initialize the server
mcp = FastMCP("chart_generation")

# @mcp.tool() # comment out for manual testing
def generate_line_chart(
    dates: list[str],
    prices: list[float],
    symbol: str = "STOCK",
    theme: dict = None,
    advanced: bool = False,
) -> Image:
    """
    Generates a financial line chart.

    Args:
        dates:      List of date/time strings. Supports ISO format, common datetime patterns
                        (e.g., "2025-03-03 14:30", "03/03/2025 14:30:15"), and time-only strings
                        (e.g., "14:30", "14:30:15") which are plotted on a dummy date.
        prices:     List of closing prices.
        symbol:     Ticker symbol shown in the chart.
        theme: Optional style overrides. Supported keys:
                - "line"          (str)   : Main line color. Default: random from red/green/blue.
                - "text"          (str)   : Axis labels, tick labels, title color. Default: "dimgrey".
                - "grid"          (str)   : Grid line color. Default: "#cccccc".
                - "background"    (str)   : Axes background. Default: "white".
                - "trend_line"    (str)   : SMA line color (advanced only). Default: "gold".
                - "line_width"    (float) : Main line width. Default: 2.
                - "marker"        (str)   : Line marker style. Default: ".".
        advanced:   When True, overlays a 3-day SMA trend line and annotates the latest price.
    """
    validate_inputs(dates, prices)
    dt_dates = parse_dates(dates)

    # Build effective theme
    effective_theme = DEFAULT_THEME.copy()
    if theme:
        effective_theme.update(theme)
    # text_color argument overrides theme's text color
    effective_theme["text"] = theme.get("text", "dimgrey")

    # Create base chart with the theme
    fig, ax = build_base_chart(dt_dates, prices, symbol, effective_theme)

    if advanced:
        # 3-day Simple Moving Average
        sma = [
            sum(prices[max(0, i - 2) : i + 1]) / len(prices[max(0, i - 2) : i + 1])
            for i in range(len(prices))
        ]
        ax.plot(
            dt_dates, sma,
            color=effective_theme.get("trend_line", "gold"),
            linestyle=effective_theme.get("trend_line_style", "--"),
            linewidth=1.5,
            label="3-Day Trend"
        )

        # Annotate the latest price
        ax.annotate(
            f"${prices[-1]:.2f}",
            xy=(dt_dates[-1], prices[-1]),
            xytext=(10, 10),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color=effective_theme.get("annotation_edge", "black")),
            bbox=dict(
                boxstyle="round,pad=0.3",
                fc=effective_theme.get("annotation_background", "yellow"),
                ec=effective_theme.get("annotation_edge", "black"),
                lw=1,
                alpha=0.8
            ),
            color=effective_theme.get("annotation_text", "black"),
        )

    return render_chart_to_image(fig)

if __name__ == "__main__":
    mcp.run()