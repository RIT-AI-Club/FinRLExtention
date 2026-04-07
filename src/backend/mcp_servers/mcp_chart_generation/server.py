"""
MCP server for chart generation
"""

import matplotlib
# CRITICAL: Set the backend to "Agg" before importing pyplot.
# This prevents the server from trying to open a GUI window, which would crash it.
matplotlib.use("Agg")
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from chart_builder_functions import *

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
        # Calculate and plot SMA 
        period = get_sma_period(dt_dates)
        sma = calculate_sma(prices, period)

        ax.plot(
            dt_dates, sma,
            color=effective_theme.get("trend_line", "gold"),
            linestyle=effective_theme.get("trend_line_style", "--"),
            linewidth=1.5,
            label=f"{period}-Day Trend"
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

    # Legend logic
    legend_loc = "upper left" if prices[-1] >= prices[0] else "upper right"
    ax.legend(loc=legend_loc)

    return render_chart_to_image(fig)

# @mcp.tool() # comment out for manual testing
def generate_candlestick_chart(
    dates: list[str],
    opens: list[float],
    highs: list[float],
    lows: list[float],  
    closes: list[float],
    symbol: str = "STOCK",
    theme: dict = None
) -> Image:
    """
    Generates a financial candlestick chart.

    Each candle shows the open, high, low, and close price for a period.
    Green candles indicate the price closed higher than it opened (bullish).
    Red candles indicate the price closed lower than it opened (bearish).

    Args:
        dates:   List of date/time strings (same formats as generate_line_chart).
        opens:   Opening prices.
        highs:   High prices for the period.
        lows:    Low prices for the period.
        closes:  Closing prices.
        symbol:  Ticker symbol shown in the chart title.
        theme:   Optional style overrides. Supports all keys from generate_line_chart, plus:
                    - "candle_up"   (str) : Bullish candle color. Default: "#109246" (green).
                    - "candle_down" (str) : Bearish candle color. Default: "#ec413e" (red).
                    - "wick"        (str) : Wick color. Default: matches body color.
    """
    validate_ohlc(dates, opens, highs, lows, closes)
    dt_dates = parse_dates(dates)

    effective_theme = DEFAULT_THEME.copy()
    if theme:
        effective_theme.update(theme)

    fig, ax = build_candlestick_chart(
        dt_dates, opens, highs, lows, closes, symbol, effective_theme
    )

    # Calculate and plot SMA 
    midpoints = [(o + c) / 2 for o, c in zip(opens, closes)]
    period = get_sma_period(dt_dates)
    sma = calculate_sma(midpoints, period)

    ax.plot(
        dt_dates, sma,
        color=effective_theme.get("trend_line", "gold"),
        linestyle=effective_theme.get("trend_line_style", "--"),
        linewidth=1.5,
        label=f"{period}-Day SMA",
        zorder = 5
    )

    # Annotate the latest price
    ax.annotate(
        f"${(opens[-1] + closes[-1])/2:.2f}",
        xy=(dt_dates[-1], (opens[-1] + closes[-1])/2),
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
        zorder = 5
    )

    # Legend logic
    legend_loc = "upper left" if closes[-1] >= opens[0] else "upper right"
    ax.legend(loc=legend_loc)
    
    return render_chart_to_image(fig)

if __name__ == "__main__":
    mcp.run()