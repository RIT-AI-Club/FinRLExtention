"""
MCP server for chart generation
"""
import matplotlib
# CRITICAL: Set the backend to 'Agg' before importing pyplot.
# This prevents the server from trying to open a GUI window, which would crash it.
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import io
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import random

COLORS = ["red", "limegreen", "royalblue"]

# Initialize the server
mcp = FastMCP("Stock Analyzer")

# @mcp.tool()
def generate_pro_financial_chart(dates: list[str], prices: list[float], symbol: str = "STOCK") -> Image:
    """
    Generates a professional-grade area chart with a moving average and trend indicators.
    """
    # Validation: Ensure data lengths match
    if len(dates) != len(prices):
        raise ValueError(f"Data mismatch: Received {len(dates)} dates and {len(prices)} prices.")

    if not dates:
        raise ValueError("Data empty: No dates or prices provided.")

    # 1. Parse Dates
    # Converting strings to datetime objects allows Matplotlib to handle axis formatting smartly.
    try:
        # Assuming ISO format (YYYY-MM-DD), adjust format string if inputs differ
        dt_dates = [datetime.fromisoformat(d) for d in dates]
    except ValueError:
        # Fallback if standard parsing fails, though explicit parsing is better
        dt_dates = dates 

    # 2. Calculate SMA (Simple Moving Average)
    sma = [sum(prices[max(0, i-2):i+1]) / len(prices[max(0, i-2):i+1]) for i in range(len(prices))]

    # 3. Setup Plot (Context Manager recommended for thread safety)
    # Using the context manager ensures styles don't leak to other threads
    with plt.style.context('ggplot'):
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # 4. Create the Area Chart
        # ax.fill_between(dt_dates, prices, color="skyblue", alpha=0.4, label="Price Area")
        ax.plot(dt_dates, prices, color=random.choice(COLORS), marker='o', linewidth=2.5, label=f"{symbol} Close")
        
        # 5. Add the Trend Line
        ax.plot(dt_dates, sma, color="gold", linestyle="--", linewidth=1.5, label="3-Day Trend")

        # 6. Highlight the Latest Price
        latest_price = prices[-1]
        latest_date = dt_dates[-1]
        
        # Note: 'dates[-1]' used in annotation needs to match the axis type (dt_dates)
        ax.annotate(f'${latest_price:.2f}', 
                    xy=(latest_date, latest_price), 
                    xytext=(10, 10), 
                    textcoords='offset points',
                    arrowprops=dict(arrowstyle='->', color='black'),
                    bbox=dict(boxstyle="round,pad=0.3", fc="yellow", ec="black", lw=1, alpha=0.8))

        # 7. Formatting
        ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Price (USD)", fontsize=12)
        ax.set_xlabel("Trading Date", fontsize=12)
        ax.legend(loc="upper left")
        ax.grid(True, linestyle=':', alpha=0.6)
        
        # Auto-format date tick labels (rotates and skips labels to fit)
        fig.autofmt_xdate()

        # 8. Save to Buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        image_bytes = buf.getvalue()
        
        # Explicitly close the figure to free memory
        plt.close(fig)

    return Image(data=image_bytes, format="png")

if __name__ == "__main__":
    mcp.run()