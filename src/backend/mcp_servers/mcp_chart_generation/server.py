"""
MCP server for chart generation
"""

import math
import matplotlib
# CRITICAL: Set the backend to "Agg" before importing pyplot.
# This prevents the server from trying to open a GUI window, which would crash it.
matplotlib.use("Agg")
from matplotlib import dates
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import io
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import random

COLORS = ["red", "limegreen", "royalblue"]
GRIDLINE_INTERVAL = 30

# Initialize the server
mcp = FastMCP("chart_generation")

def _build_base_chart(
    dt_dates: list,
    prices: list[float],
    symbol: str,
    text_color: str,
    color: str,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Creates and returns a base (fig, ax) with shared formatting applied.
    Intended as an internal helper — not for direct use.
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    ax.plot(dt_dates, prices, color=color, marker=".", linewidth=2, label=f"{symbol} Close", clip_on=False)

    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price
    y_min = math.floor((min_price - price_range * 0.3) / GRIDLINE_INTERVAL) * GRIDLINE_INTERVAL # calculates the minimum y of the graph and makes it land on a grid interval
    y_max = math.ceil((max_price + price_range * 0.2) / GRIDLINE_INTERVAL) * GRIDLINE_INTERVAL # calculates the maximum y of the graph and makes it land on a grid interval
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(dt_dates[0], dt_dates[-1])

    ax.set_facecolor("white")
    fig.patch.set_alpha(0.0)
    ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight="bold", pad=20)
    ax.set_ylabel("Price (USD)", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
    ax.set_xlabel("Trading Date", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
    ax.xaxis.set_major_formatter(dates.DateFormatter("%m-%d-%Y"))  # e.g. "01-01-2024"
    ax.tick_params(axis="both", labelcolor=text_color)
    ax.yaxis.grid(True, which="both", linestyle=":", alpha=0.75, color="#cccccc")
    fig.autofmt_xdate()

    return fig, ax
    
def _render_chart_to_image(fig: plt.Figure) -> Image:
    """Saves a Matplotlib figure to a PNG Image object and cleans up."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)  # explicitly save THIS figure
    buffer.seek(0)
    image_bytes = buffer.getvalue()
    plt.close(fig)
    return Image(data=image_bytes, format="png")

def _parse_dates(dates: list[str]) -> list:
    """Converts ISO date strings to datetime objects, with a graceful fallback."""
    try:
        return [datetime.fromisoformat(d) for d in dates]
    except ValueError:
        return dates

def _validate_inputs(dates: list, prices: list[float]) -> None:
    """Raises ValueError for mismatched or empty inputs."""
    if not dates:
        raise ValueError("Data empty: No dates or prices provided.")
    if len(dates) != len(prices):
        raise ValueError(f"Data mismatch: Received {len(dates)} dates and {len(prices)} prices.")

# @mcp.tool() # comment out for manual testing
def generate_line_chart(
    dates: list[str],
    prices: list[float],
    symbol: str = "STOCK",
    text_color: str = "dimgrey",
    advanced: bool = False,
) -> Image:
    """
    Generates a financial line chart.

    Args:
        dates:      List of ISO-format date strings (YYYY-MM-DD).
        prices:     List of closing prices corresponding to each date.
        symbol:     Ticker symbol shown in the chart title and legend.
        text_color: Color used for axis labels and tick labels.
        advanced:   When True, overlays a 3-day SMA trend line and annotates
                    the latest price. When False, produces a clean basic chart.
    """
    _validate_inputs(dates, prices)
    dt_dates = _parse_dates(dates)
    color = random.choice(COLORS)

    with plt.style.context("ggplot"):
        fig, ax = _build_base_chart(dt_dates, prices, symbol, text_color, color)

        if advanced:
            # 3-day Simple Moving Average
            sma = [
                sum(prices[max(0, i - 2) : i + 1]) / len(prices[max(0, i - 2) : i + 1])
                for i in range(len(prices))
            ]
            ax.plot(dt_dates, sma, color="gold", linestyle="--", linewidth=1.5, label="3-Day Trend")

            # Annotate the latest price
            ax.annotate(
                f"${prices[-1]:.2f}",
                xy=(dt_dates[-1], prices[-1]),
                xytext=(10, 10),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="black"),
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", ec="black", lw=1, alpha=0.8),
                color="black",
            )

            legend_loc = "upper left" if prices[-1] >= prices[0] else "upper right"
            ax.legend(loc=legend_loc)

        return _render_chart_to_image(fig)

if __name__ == "__main__":
    mcp.run()