"""
MCP server for chart generation
"""

import math
import matplotlib
# CRITICAL: Set the backend to "Agg" before importing pyplot.
# This prevents the server from trying to open a GUI window, which would crash it.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import random

COLORS = ["red", "limegreen", "royalblue"]
GRIDLINE_INTERVAL = 5

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

    ax.plot(dt_dates, prices, color=color, marker=".", linewidth=2, label=f"{symbol} Close")

    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price
    y_min = math.floor((min_price - price_range * 0.5) / GRIDLINE_INTERVAL) * GRIDLINE_INTERVAL # calculates the minimum y of the graph and makes it land on a grid interval
    y_max = math.ceil((max_price + price_range * 0.2) / GRIDLINE_INTERVAL) * GRIDLINE_INTERVAL # calculates the maximum y of the graph and makes it land on a grid interval
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(dt_dates[0], dt_dates[-1]) # sets the first point to be on the y-axis

    ax.set_facecolor("white")
    fig.patch.set_alpha(0.0)
    ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight="bold", pad=20)
    ax.set_ylabel("Price (USD)", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
    ax.set_xlabel("Trading Date", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
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
    
# -------------------------------OLD TOOLS-------------------------------
# # @mcp.tool() # comment out for manual testing
# def generate_financial_line_chart(dates: list[str], prices: list[float], symbol: str = "STOCK", text_color: str = "dimgrey") -> Image:
#     """
#     Generates a detailed financial line chart with a moving average and trend indicators.
#     """
#     # Validation: Ensure data lengths match
#     if len(dates) != len(prices):
#         raise ValueError(f"Data mismatch: Received {len(dates)} dates and {len(prices)} prices.")

#     if not dates:
#         raise ValueError("Data empty: No dates or prices provided.")

#     # Format dates
#     # Convert strings to datetime objects allows Matplotlib to handle axis formatting smartly.
#     try:
#         # Assuming dates are in ISO format (YYYY-MM-DD)
#         dt_dates = [datetime.fromisoformat(d) for d in dates] 
#     except ValueError:
#         # Fallback if standard parsing fails
#         dt_dates = dates 

#     # Calculate SMA (Simple Moving Average)
#     sma = [sum(prices[max(0, i-2):i+1]) / len(prices[max(0, i-2):i+1]) for i in range(len(prices))]

#     # Setup plot
#     # Context manager ensures styles don"t leak to other threads
#     with plt.style.context("ggplot"):
#         fig, ax = plt.subplots(figsize=(12, 7))
        
#         # Plot the Line Graph
#         ax.plot(dt_dates, prices, color=random.choice(COLORS), marker=".", linewidth=2, label=f"{symbol} Close")

#         # Add padding on vertical axis so that legend never covers the graph
#         min_prices = min(prices)
#         max_prices = max(prices)
#         price_range = max_prices - min_prices
#         ax.set_ylim(min_prices - price_range * 0.5, max_prices + price_range * 0.2) # padding for bottom and padding for legend at top
        
#         # Add the Trend Line
#         ax.plot(dt_dates, sma, color="gold", linestyle="--", linewidth=1.5, label="3-Day Trend")

#         # Highlight the Latest Price
#         latest_price = prices[-1]
#         latest_date = dt_dates[-1]
        
#         # Note: "dates[-1]" used in annotation needs to match the axis type (dt_dates)
#         ax.annotate(f"${latest_price:.2f}", 
#                     xy=(latest_date, latest_price), 
#                     xytext=(10, 10), 
#                     textcoords="offset points",
#                     arrowprops=dict(arrowstyle="->", color="black"),
#                     bbox=dict(boxstyle="round,pad=0.3", fc="yellow", ec="black", lw=1, alpha=0.8),
#                     color="black")

#         # Formatting
#         ax.set_facecolor("white") # set chart background
#         fig.patch.set_alpha(0.0) # set transparent figure background
#         ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight="bold", pad=20)
#         ax.set_ylabel("Price (USD)", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
#         ax.set_xlabel("Trading Date", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
#         ax.tick_params(axis='both', labelcolor=text_color)
#         if prices[-1] >= prices[0]: # determine legend placement
#             ax.legend(loc="upper left")
#         else:
#             ax.legend(loc="upper right")
#         ax.yaxis.set_minor_locator(MultipleLocator(5)) # minor gridline every 5 units
#         ax.yaxis.grid(True, which="both", linestyle=":", alpha=0.75, color="#cccccc") # set horizontal grid style and color
        
#         # Auto-format date tick labels (rotates and skips labels to fit)
#         fig.autofmt_xdate()

#         # Save to Buffer
#         buffer = io.BytesIO()
#         plt.savefig(buffer, format="png", dpi=120)
#         buffer.seek(0)
#         image_bytes = buffer.getvalue()
        
#         # Explicitly close the figure to free memory
#         plt.close(fig)

#     return Image(data=image_bytes, format="png")

# # @mcp.tool() # comment out for manual testing
# def generate_basic_line_chart(dates: list[str], prices: list[float], symbol: str = "STOCK", text_color: str = "dimgrey") -> Image:
#     """
#     Generates a basic line chart to represent financial data.
#     """
#     # Validation: Ensure data lengths match
#     if len(dates) != len(prices):
#         raise ValueError(f"Data mismatch: Received {len(dates)} dates and {len(prices)} prices.")

#     if not dates:
#         raise ValueError("Data empty: No dates or prices provided.")

#     # Format dates
#     # Convert strings to datetime objects allows Matplotlib to handle axis formatting smartly.
#     try:
#         # Assuming dates are in ISO format (YYYY-MM-DD)
#         dt_dates = [datetime.fromisoformat(d) for d in dates] 
#     except ValueError:
#         # Fallback if standard parsing fails
#         dt_dates = dates 

#     # Setup plot
#     # Context manager ensures styles don"t leak to other threads
#     with plt.style.context("ggplot"):
#         fig, ax = plt.subplots(figsize=(12, 7))
        
#         # Plot the Line Graph
#         ax.plot(dt_dates, prices, color=COLOR, marker=".", linewidth=2)

#         # Add padding on vertical axis so that legend never covers the graph
#         min_prices = min(prices)
#         max_prices = max(prices)
#         price_range = max_prices - min_prices
#         ax.set_ylim(min_prices - price_range * 0.5, max_prices + price_range * 0.2) # padding for top and bottom

#         # Formatting
#         ax.set_facecolor("white") # set chart background
#         fig.patch.set_alpha(0.0) # set transparent figure background
#         ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight="bold", pad=20)
#         ax.set_ylabel("Price (USD)", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
#         ax.set_xlabel("Trading Date", fontsize=12, labelpad=10, fontweight="bold", color=text_color)
#         ax.tick_params(axis='both', labelcolor=text_color)
#         ax.yaxis.set_minor_locator(MultipleLocator(5)) # minor gridline every 5 units
#         ax.yaxis.grid(True, which="both", linestyle=":", alpha=0.75, color="#cccccc") # set grid style and color
        
#         # Auto-format date tick labels (rotates and skips labels to fit)
#         fig.autofmt_xdate()

#         # Save to Buffer
#         buffer = io.BytesIO()
#         plt.savefig(buffer, format="png", dpi=120)
#         buffer.seek(0)
#         image_bytes = buffer.getvalue()
        
#         # Explicitly close the figure to free memory
#         plt.close(fig)

#     return Image(data=image_bytes, format="png")

if __name__ == "__main__":
    mcp.run()