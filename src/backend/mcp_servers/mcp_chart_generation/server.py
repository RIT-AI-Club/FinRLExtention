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
import matplotlib.dates as mdates
import io
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import random

# Line colors for generated chart
COLORS = ["red", "limegreen", "royalblue"]

# Control the gridline interval
GRIDLINE_INTERVAL = 30

# Common datetime formats (date + time) to try
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",   # 2025-03-03 14:30:15.123456
    "%Y-%m-%d %H:%M:%S",       # 2025-03-03 14:30:15
    "%Y-%m-%d %H:%M",          # 2025-03-03 14:30
    "%Y/%m/%d %H:%M:%S.%f",    # 2025/03/03 14:30:15.123456
    "%Y/%m/%d %H:%M:%S",       # 2025/03/03 14:30:15
    "%Y/%m/%d %H:%M",          # 2025/03/03 14:30
    "%m/%d/%Y %H:%M:%S.%f",    # 03/03/2025 14:30:15.123456
    "%m/%d/%Y %H:%M:%S",       # 03/03/2025 14:30:15
    "%m/%d/%Y %H:%M",          # 03/03/2025 14:30
    "%d-%m-%Y %H:%M:%S.%f",    # 03-03-2025 14:30:15.123456
    "%d-%m-%Y %H:%M:%S",       # 03-03-2025 14:30:15
    "%d-%m-%Y %H:%M",          # 03-03-2025 14:30
]

# Common time-only formats (to be combined with a dummy date)
TIME_FORMATS = [
    "%H:%M:%S.%f",   # 14:30:15.123456
    "%H:%M:%S",      # 14:30:15
    "%H:%M",         # 14:30
]

# Dummy date for time‑only inputs
DUMMY_DATE = datetime(2000, 1, 1)

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

    # Format y-axis ticks to two decimal places if prices are within 100
    if max(prices) < 25:
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
    
    # Align data points to start on y-axis (x=0)
    ax.set_xlim(dt_dates[0], dt_dates[-1]) 

    ax.set_facecolor("white")
    fig.patch.set_alpha(0.0)
    ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight="bold", pad=20)
    ax.set_ylabel("Price (USD)", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
    ax.set_xlabel("Trading Date", fontsize=12, labelpad=10, fontweight="bold", color=text_color)

    # Determine total time spanned
    span = dt_dates[-1] - dt_dates[0]
    total_hours = span.total_seconds() / 3600.0
    total_days = span.days + span.seconds / 86400.0

    # Choose locator and formatter based on the table
    if total_hours <= 1:                     # ≤1 hour → 5‑minute ticks
        locator = mdates.MinuteLocator(interval=5)
        fmt = '%H:%M'
    elif total_hours <= 2:                   # 1–2 hours → 15‑minute ticks
        locator = mdates.MinuteLocator(interval=15)
        fmt = '%H:%M'
    elif total_hours <= 6:                   # 2–6 hours → 30‑minute ticks
        locator = mdates.MinuteLocator(interval=30)
        fmt = '%H:%M'
    elif total_hours <= 12:                  # 6–12 hours → 1‑hour ticks
        locator = mdates.HourLocator(interval=1)
        fmt = '%H:%M'
    elif total_hours <= 24:                  # 12–24 hours → 2‑hour ticks
        locator = mdates.HourLocator(interval=2)
        fmt = '%H:%M'
    elif total_days <= 3:                    # 1–3 days → 6‑hour ticks
        locator = mdates.HourLocator(interval=6)
        fmt = '%m/%d %H:%M'
    elif total_days <= 7:                    # 3–7 days → 1‑day ticks
        locator = mdates.DayLocator(interval=1)
        fmt = '%m/%d'
    elif total_days <= 28:                   # 1–4 weeks → 2‑day ticks
        locator = mdates.DayLocator(interval=2)
        fmt = '%m/%d'
    elif total_days <= 90:                   # 1–3 months → 1‑week ticks
        locator = mdates.WeekdayLocator(interval=1)
        fmt = '%m/%d'
    elif total_days <= 365:                  # 3–12 months → 1‑month ticks
        locator = mdates.MonthLocator(interval=1)
        fmt = '%Y-%m'
    else:                                    # >1 year → quarterly ticks
        locator = mdates.MonthLocator(interval=3)
        fmt = '%Y'

    # Apply locator and formatter
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))

    # Set tick paramaters, gridlines
    ax.tick_params(axis="both", labelcolor=text_color)
    ax.yaxis.grid(True, which="both", linestyle=":", alpha=0.75, color="#cccccc")

    # Apply legend
    legend_loc = "upper left" if prices[-1] >= prices[0] else "upper right"
    ax.legend(loc=legend_loc)

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

def _parse_dates(dates: list[str]) -> list[datetime]:
    """
    Convert a list of date/time strings to datetime objects.

    Supports:
      - ISO format (via fromisoformat)
      - Common datetime formats listed in DATETIME_FORMATS
      - Time‑only formats (combined with DUMMY_DATE)

    Raises ValueError if a string cannot be parsed.
    """
    parsed = []
    for d in dates:
        dt = None

        # 1. Try Python's built‑in ISO parser (handles both 'T' and space)
        try:
            dt = datetime.fromisoformat(d)
            parsed.append(dt)
            continue
        except ValueError:
            pass

        # 2. Try each full datetime format
        for fmt in DATETIME_FORMATS:
            try:
                dt = datetime.strptime(d, fmt)
                parsed.append(dt)
                break
            except ValueError:
                continue
        if dt is not None:
            continue

        # 3. Try each time‑only format (combine with dummy date)
        for fmt in TIME_FORMATS:
            try:
                time_part = datetime.strptime(d, fmt).time()
                dt = datetime.combine(DUMMY_DATE, time_part)
                parsed.append(dt)
                break
            except ValueError:
                continue
        if dt is not None:
            continue

        # 4. No format matched
        raise ValueError(f"Unrecognized date/time format: {d}")

    return parsed

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
        dates:      List of ISO-format date strings (YYYY-MM-DD) OR time strings (HH:MM:SS).
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

        return _render_chart_to_image(fig)

if __name__ == "__main__":
    mcp.run()