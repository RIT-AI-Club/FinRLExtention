"""
Helper functions for MCP chart generation
"""

import matplotlib
# CRITICAL: Set the backend to "Agg" before importing pyplot.
# This prevents the server from trying to open a GUI window, which would crash it.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import random
import numpy as np

# Default colors
COLORS = ["red", "limegreen", "royalblue"]

# Control the number of ticks
TICK_NUMBER = 6

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

def build_base_chart(
    dt_dates: list,
    prices: list[float],
    symbol: str,
    theme: dict,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Creates and returns a base (fig, ax) with shared formatting applied.
    Intended as an internal helper — not for direct use.
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    # Use theme for line color, width, and marker
    line_color = theme["line"] if theme["line"] is not None else random.choice(COLORS)
    ax.plot(
        dt_dates, prices,
        color=line_color,
        marker=theme.get("marker", "."),
        linewidth=theme.get("line_width", 2),
        label=f"{symbol} Close",
        clip_on=False,
        zorder=5
    )

    # Format y-axis ticks to two decimal places if prices are within 100
    ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
    
    # Set x-axis limit exactly to data range
    ax.set_xlim(dt_dates[0], dt_dates[-1]) 
    
    # Calculate y-axis limits with a small amount of padding (5% on each side)
    y_min = min(prices)
    y_max = max(prices)
    y_range = y_max - y_min
    padding_factor = 0.05   # 5% padding

    if y_range == 0:
        # If all prices are the same, use a small absolute padding
        y_pad = abs(y_min) * 0.01 if y_min != 0 else 1.0
    else:
        y_pad = padding_factor * y_range

    # Avoid extending below zero (prices can't be negative)
    if y_min - y_pad < 0:
        ax.set_ylim(y_min, y_max + y_pad)   # pad only the top
    else:
        ax.set_ylim(y_min - y_pad, y_max + y_pad)

    # Axes colors
    ax.set_facecolor(theme.get("background", "white"))
    fig.patch.set_alpha(0.0)

    # Title and labels with theme text color
    text_color = theme["text"]
    ax.set_title(
        f"Financial Performance Analysis: {symbol}",
        fontsize=16, fontweight="bold", pad=20,
        color=text_color
    )
    ax.set_ylabel("Price (USD)", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
    ax.set_xlabel("Trading Date", fontsize=12, labelpad=10, fontweight="bold", color=text_color)

    # Calculate and apply locator and formatter to axis
    locator, formatter = get_date_locator_and_formatter(dt_dates)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Evenly space X and Y ticks
    xmin, xmax = ax.get_xlim()
    xticks = np.linspace(xmin, xmax, TICK_NUMBER)   # evenly spaced
    ax.set_xticks(xticks)

    ymin, ymax = ax.get_ylim()
    yticks = np.linspace(ymin, ymax, TICK_NUMBER)
    ax.set_yticks(yticks)

    # Grid and tick parameters using theme
    ax.tick_params(axis="both", labelcolor=text_color)
    ax.yaxis.grid(
        True, which="both",
        linestyle=":", alpha=0.75,
        color=theme.get("grid", "#cccccc")
    )

    # Legend logic
    legend_loc = "upper left" if prices[-1] >= prices[0] else "upper right"
    ax.legend(loc=legend_loc)

    # Format x‑axis labels
    fig.autofmt_xdate(rotation=0, ha="center")
    labels = ax.get_xticklabels()
    if labels:
        labels[0].set_horizontalalignment("left")

    return fig, ax
    
def render_chart_to_image(fig: plt.Figure) -> Image:
    """Saves a Matplotlib figure to a PNG Image object and cleans up."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)  # explicitly save figure
    buffer.seek(0)
    image_bytes = buffer.getvalue()
    plt.close(fig)
    return Image(data=image_bytes, format="png")

def parse_dates(dates: list[str]) -> list[datetime]:
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

def validate_inputs(dates: list, prices: list[float]) -> None:
    """Raises ValueError for mismatched or empty inputs."""
    if not dates:
        raise ValueError("Data empty: No dates or prices provided.")
    if len(dates) != len(prices):
        raise ValueError(f"Data mismatch: Received {len(dates)} dates and {len(prices)} prices.")

def validate_ohlc(
    dates: list,
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> None:
    """Raises ValueError for invalid or mismatched OHLC inputs.

    Checks that:
    - No list is empty.
    - All five lists share the same length.
    - For every candle, high >= low.
    """
    if not dates:
        raise ValueError("Data empty: No dates or prices provided.")

    lengths = {"opens": len(opens), "highs": len(highs), "lows": len(lows), "closes": len(closes)}
    for name, length in lengths.items():
        if length != len(dates):
            raise ValueError(
                f"Data mismatch: Received {len(dates)} dates but {length} {name}."
            )

    for i, (h, l) in enumerate(zip(highs, lows)):
        if h < l:
            raise ValueError(
                f"Invalid OHLC data at index {i}: high ({h}) is less than low ({l})."
            )
        
def build_candlestick_chart(
    dt_dates: list,
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    symbol: str,
    theme: dict,
) -> tuple[plt.Figure, plt.Axes]:
    """Builds and returns a candlestick (fig, ax) with shared formatting applied.

    Each candle is drawn with:
    - A thin vertical line (wick) from low to high using ax.vlines().
    - A filled rectangle (body) from open to close using ax.bar().
      Green when close >= open, red otherwise.

    Args:
        dt_dates: Parsed datetime objects, one per candle.
        opens:    Opening prices.
        highs:    High prices.
        lows:     Low prices.
        closes:   Closing prices.
        symbol:   Ticker symbol shown in the chart title.
        theme:    Style dictionary (same schema as line chart themes).

    Returns:
        A (fig, ax) tuple ready to be rendered or further annotated.
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    # Compute a sensible candle width (80% of the smallest gap between dates)
    if len(dt_dates) > 1:
        gaps = [(dt_dates[i + 1] - dt_dates[i]).total_seconds() for i in range(len(dt_dates) - 1)]
        min_gap_days = min(gaps) / 86400.0
        candle_width = min_gap_days * 0.8
    else:
        candle_width = 0.6  # fallback for a single candle

    bull_color = theme.get("candle_up", "#109246")    # green default
    bear_color = theme.get("candle_down", "#ec413e")  # red default
    wick_color = theme.get("wick", None)              # None → match body color

    # Draw wicks and bodies for each candle
    for i, (date, open, high, low, close) in enumerate(
        zip(dt_dates, opens, highs, lows, closes)
    ):
        is_bull = close >= open
        body_color = bull_color if is_bull else bear_color
        wc = wick_color if wick_color else body_color

        # Wick: thin line from low to high
        ax.vlines(date, low, high, color=wc, linewidth=1, zorder=4)

        # Body: rectangle from open to close
        body_bottom = min(open, close)
        body_height = abs(close - open)
        ax.bar(
            date,
            body_height,
            bottom=body_bottom,
            width=candle_width,
            color=body_color,
            edgecolor=wc,
            linewidth=0.5,
            zorder=5,
        )

    # --- Shared formatting (mirrors build_base_chart) ---
    text_color = theme["text"]

    ax.set_facecolor(theme.get("background", "white"))
    fig.patch.set_alpha(0.0)

    ax.set_title(
        f"Financial Performance Analysis: {symbol}",
        fontsize=16, fontweight="bold", pad=20, color=text_color,
    )
    ax.set_ylabel("Price (USD)", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
    ax.set_xlabel("Trading Date", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
    ax.tick_params(axis="both", labelcolor=text_color)
    ax.yaxis.set_major_formatter(plt.FormatStrFormatter("%.2f"))
    ax.yaxis.grid(
        True, which="both",
        linestyle=":", alpha=0.75,
        color=theme.get("grid", "#cccccc"),
    )

    # Y-axis limits with 5% padding
    y_min = min(lows)
    y_max = max(highs)
    y_range = y_max - y_min
    y_pad = (0.05 * y_range) if y_range != 0 else (abs(y_min) * 0.01 or 1.0)
    ax.set_ylim(
        y_min - y_pad if y_min - y_pad >= 0 else y_min,
        y_max + y_pad,
    )

    # X-axis limits: half a candle width of breathing room on each side
    half_width = candle_width / 2.0
    ax.set_xlim(
        mdates.date2num(dt_dates[0]) - half_width,
        mdates.date2num(dt_dates[-1]) + half_width,
    )

    locator, formatter = get_date_locator_and_formatter(dt_dates)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    
    # Evenly space X and Y ticks
    xmin, xmax = ax.get_xlim()
    xticks = np.linspace(xmin, xmax, TICK_NUMBER)   # evenly spaced
    ax.set_xticks(xticks)

    ymin, ymax = ax.get_ylim()
    yticks = np.linspace(ymin, ymax, TICK_NUMBER)
    ax.set_yticks(yticks)

    fig.autofmt_xdate(rotation=0, ha="center")
    labels = ax.get_xticklabels()
    if labels:
        labels[0].set_horizontalalignment("left")

    return fig, ax

def get_date_locator_and_formatter(dt_dates: list) -> tuple[mdates.DateLocator, mdates.DateFormatter]:
    """
    Selects an appropriate x-axis tick locator and date formatter based on
    the total time span of the provided datetime list.

    Intended as an internal helper for build_base_chart and
    build_candlestick_chart — call it instead of duplicating this logic.

    Args:
        dt_dates: A list of parsed datetime objects in chronological order.

    Returns:
        A (locator, formatter) tuple ready to be passed to:
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
    """
    span = dt_dates[-1] - dt_dates[0]
    total_hours = span.total_seconds() / 3600.0
    total_days  = span.days + span.seconds / 86400.0

    if total_hours <= 1:                     # ≤1 hour       → 5-minute ticks
        locator = mdates.MinuteLocator(interval=5)
        fmt = "%I:%M %p"
    elif total_hours <= 2:                   # 1–2 hours     → 15-minute ticks
        locator = mdates.MinuteLocator(interval=15)
        fmt = "%I:%M %p"
    elif total_hours <= 6:                   # 2–6 hours     → 30-minute ticks
        locator = mdates.MinuteLocator(interval=30)
        fmt = "%I:%M %p"
    elif total_hours <= 12:                  # 6–12 hours    → 1-hour ticks
        locator = mdates.HourLocator(interval=1)
        fmt = "%I:%M %p"
    elif total_hours <= 24:                  # 12–24 hours   → 2-hour ticks
        locator = mdates.HourLocator(interval=2)
        fmt = "%I:%M %p"
    elif total_days <= 3:                    # 1–3 days      → 6-hour ticks
        locator = mdates.HourLocator(interval=6)
        fmt = "%m/%d %I:%M %p"
    elif total_days <= 7:                    # 3–7 days      → 1-day ticks
        locator = mdates.DayLocator(interval=1)
        fmt = "%m/%d"
    elif total_days <= 28:                   # 1–4 weeks     → 2-day ticks
        locator = mdates.DayLocator(interval=2)
        fmt = "%m/%d"
    elif total_days <= 90:                   # 1–3 months    → 1-week ticks
        locator = mdates.WeekdayLocator(interval=1)
        fmt = "%m/%d"
    elif total_days <= 365:                  # 3–12 months   → 1-month ticks
        locator = mdates.MonthLocator(interval=1)
        fmt = "%Y-%m"
    else:                                    # >1 year       → quarterly ticks
        locator = mdates.MonthLocator(interval=3)
        fmt = "%Y"

    return locator, mdates.DateFormatter(fmt)