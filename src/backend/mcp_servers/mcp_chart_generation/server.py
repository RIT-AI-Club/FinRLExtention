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
mcp = FastMCP("chart_generation")

# @mcp.tool() # comment out for testing
def generate_financial_line_chart(dates: list[str], prices: list[float], symbol: str = "STOCK") -> Image:
    """
    Generates a detailed financial line chart with a moving average and trend indicators.
    """
    # Validation: Ensure data lengths match
    if len(dates) != len(prices):
        raise ValueError(f"Data mismatch: Received {len(dates)} dates and {len(prices)} prices.")

    if not dates:
        raise ValueError("Data empty: No dates or prices provided.")

    # Format dates
    # Convert strings to datetime objects allows Matplotlib to handle axis formatting smartly.
    try:
        # Assuming dates are in ISO format (YYYY-MM-DD)
        dt_dates = [datetime.fromisoformat(d) for d in dates] 
    except ValueError:
        # Fallback if standard parsing fails
        dt_dates = dates 

    # Calculate SMA (Simple Moving Average)
    sma = [sum(prices[max(0, i-2):i+1]) / len(prices[max(0, i-2):i+1]) for i in range(len(prices))]

    # Setup plot
    # Context manager ensures styles don't leak to other threads
    with plt.style.context('ggplot'):
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Plot the Line Graph
        ax.plot(dt_dates, prices, color=random.choice(COLORS), marker='.', linewidth=2, label=f"{symbol} Close")

        # Add padding on vertical axis so that legend never covers the graph
        min_prices = min(prices)
        max_prices = max(prices)
        price_range = max_prices - min_prices
        ax.set_ylim(min_prices - price_range * 0.1, max_prices + price_range * 0.2) # padding for bottom and padding for legend at top
        
        # Add the Trend Line
        ax.plot(dt_dates, sma, color="gold", linestyle="--", linewidth=1.5, label="3-Day Trend")

        # Highlight the Latest Price
        latest_price = prices[-1]
        latest_date = dt_dates[-1]
        
        # Note: 'dates[-1]' used in annotation needs to match the axis type (dt_dates)
        ax.annotate(f'${latest_price:.2f}', 
                    xy=(latest_date, latest_price), 
                    xytext=(10, 10), 
                    textcoords='offset points',
                    arrowprops=dict(arrowstyle='->', color='black'),
                    bbox=dict(boxstyle="round,pad=0.3", fc="yellow", ec="black", lw=1, alpha=0.8))

        # Formatting
        ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Price (USD)", fontsize=12)
        ax.set_xlabel("Trading Date", fontsize=12)
        if prices[-1] >= prices[0]:
            ax.legend(loc="upper left")
        else:
            ax.legend(loc="upper right")
        ax.grid(True, linestyle=':', alpha=0.6)
        
        # Auto-format date tick labels (rotates and skips labels to fit)
        fig.autofmt_xdate()

        # Save to Buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=120)
        buffer.seek(0)
        image_bytes = buffer.getvalue()
        
        # Explicitly close the figure to free memory
        plt.close(fig)

    return Image(data=image_bytes, format="png")

# @mcp.tool() # comment out for testing
def generate_basic_line_chart(dates: list[str], prices: list[float], symbol: str = "STOCK") -> Image:
    """
    Generates a basic line chart to represent financial data.
    """
    # Validation: Ensure data lengths match
    if len(dates) != len(prices):
        raise ValueError(f"Data mismatch: Received {len(dates)} dates and {len(prices)} prices.")

    if not dates:
        raise ValueError("Data empty: No dates or prices provided.")

    # Format dates
    # Convert strings to datetime objects allows Matplotlib to handle axis formatting smartly.
    try:
        # Assuming dates are in ISO format (YYYY-MM-DD)
        dt_dates = [datetime.fromisoformat(d) for d in dates] 
    except ValueError:
        # Fallback if standard parsing fails
        dt_dates = dates 

    # Setup plot
    # Context manager ensures styles don't leak to other threads
    with plt.style.context('ggplot'):
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Plot the Line Graph
        ax.plot(dt_dates, prices, color=random.choice(COLORS), marker='.', linewidth=2)

        # Add padding on vertical axis so that legend never covers the graph
        min_prices = min(prices)
        max_prices = max(prices)
        price_range = max_prices - min_prices
        ax.set_ylim(min_prices - price_range * 0.1) # padding for top and bottom

        # Formatting
        ax.set_title(f"Financial Performance Analysis: {symbol}", fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Price (USD)", fontsize=12)
        ax.set_xlabel("Trading Date", fontsize=12)
        ax.grid(True, linestyle=':', alpha=0.6)
        
        # Auto-format date tick labels (rotates and skips labels to fit)
        fig.autofmt_xdate()

        # Save to Buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=120)
        buffer.seek(0)
        image_bytes = buffer.getvalue()
        
        # Explicitly close the figure to free memory
        plt.close(fig)

    return Image(data=image_bytes, format="png")

if __name__ == "__main__":
    mcp.run()