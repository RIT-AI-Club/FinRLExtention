from fastmcp import FastMCP
from fastmcp.utilities.types import Image
import matplotlib.pyplot as plt
import io

# Initialize the server
mcp = FastMCP("Financial Chart Server")

@mcp.tool()
def plot_stock_price(dates: list[str], prices: list[float], symbol: str = "STOCK") -> Image:
    """
    Generates a line chart for a stock's price history.
    
    Args:
        dates: A list of dates (strings, e.g., '2023-01-01')
        prices: A list of corresponding prices (floats)
        symbol: The stock ticker symbol (e.g., 'AAPL') to display in the title
    """
    
    # 1. Create the figure using Matplotlib
    plt.figure(figsize=(10, 6))
    plt.plot(dates, prices, marker='o', linestyle='-', color='b')
    
    # 2. Styling the chart
    plt.title(f"{symbol} Price History")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 3. Save the plot to an in-memory buffer (instead of a file on disk)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # 4. Read the bytes
    image_data = buf.getvalue()
    
    # 5. Close the plot to free memory
    plt.close()
    
    # 6. Return as a FastMCP Image object
    return Image(data=image_data, format="png")

if __name__ == "__main__":
    mcp.run()