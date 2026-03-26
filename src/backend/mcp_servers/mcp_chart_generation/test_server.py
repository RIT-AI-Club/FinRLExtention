"""
Run this program to test the chart generation MCP server
"""

from server import *
from datetime import datetime, timedelta
import random
from example_themes import *

THEMES = [NVIDIA_THEME, AMD_THEME, META_THEME, X_THEME]

START_PRICE = 76.12 # start price for dummy prices
PRICE_DEVIATION = 2.5 # how far a new price may deviate from the last price
NUMBER_OF_POINTS = 60 # number of price points (corresponds with date/time points)

WICK_EXTENSION = 1.5 # max extra range beyond open/close for high/low wicks

def test_chart_generation(advanced):
    print("Starting local test of Stock Analyzer...")

    # 1. Simulate Data: Generate dummy stock data
    # This mimics the JSON arguments Gemini would pass to the tool
    base_date = datetime.now()
    dates = [(base_date - timedelta(weeks=i)).isoformat() for i in range(52)] # 1-YEAR weekly trend
    # dates = [(base_date - timedelta(days=i)).isoformat() for i in range(30)] # 1-MONTH daily trend
    # dates = [(base_date - timedelta(days=i)).isoformat() for i in range(14)] # 2-WEEK daily trend
    # dates = [(base_date - timedelta(hours=i)).isoformat() for i in range(72)] #  3-DAY hourly trend
    # dates = [(base_date - timedelta(hours=i)).isoformat() for i in range(24)] # 1-DAY hourly trend
    # dates = [(base_date - timedelta(minutes=i)).isoformat() for i in range(60)] # 1-HOUR minutely trend
    dates.reverse() # Sort chronologically

    # create a random walk for price
    prices = [START_PRICE] # start price
    for _ in range(NUMBER_OF_POINTS - 1):
        change = random.uniform(-PRICE_DEVIATION, PRICE_DEVIATION)
        new_price = prices[-1] + change
        if new_price < 0:
            new_price = 0
        prices.append(new_price)

    print(f"Generated {len(dates)} pieces of sample data.")

    # 2. Call the Tool Directly
    try:
        print("calling chart_generator()...")
        image_result = generate_line_chart(dates=dates, prices=prices, symbol="TEST-CO", advanced=advanced, theme=random.choice(THEMES))
        
        # 3. Save the output to verify visual correctness
        output_filename = "src/backend/charts/test_chart_output.png"
        with open(output_filename, "wb") as f:
            f.write(image_result.data)
            
        print(f"Success! Image saved to '{output_filename}'")
        print("Please open this file to verify the layout, dates, and styles.")

    except Exception as e:
        print(f"Error during generation: {e}")

def test_candlestick_generation():
    print("Starting local test of Candlestick Chart...")
 
    # 1. Simulate Data: Generate dummy OHLC stock data
    base_date = datetime.now()
    # dates = [(base_date - timedelta(weeks=i)).isoformat() for i in range(52)] # 1-YEAR weekly trend
    # dates = [(base_date - timedelta(days=i)).isoformat() for i in range(30)] # 1-MONTH daily trend
    # dates = [(base_date - timedelta(days=i)).isoformat() for i in range(14)] # 2-WEEK daily trend
    # dates = [(base_date - timedelta(hours=i)).isoformat() for i in range(72)] #  3-DAY hourly trend
    # dates = [(base_date - timedelta(hours=i)).isoformat() for i in range(24)] # 1-DAY hourly trend
    dates = [(base_date - timedelta(minutes=i)).isoformat() for i in range(60)] # 1-HOUR minutely trend
    dates.reverse() # Sort chronologically
 
    # Generate OHLC data via a random walk.
    # Each candle's open is the previous candle's close, keeping the series continuous.
    # High/low wicks extend randomly beyond the open/close body.
    opens, highs, lows, closes = [], [], [], []
    current_price = START_PRICE
 
    for _ in range(NUMBER_OF_POINTS):
        open_price = current_price
 
        # Close drifts randomly from the open
        close_price = open_price + random.uniform(-PRICE_DEVIATION, PRICE_DEVIATION)
        close_price = max(close_price, 0.01) # floor at near-zero to avoid negatives
 
        candle_top    = max(open_price, close_price)
        candle_bottom = min(open_price, close_price)
 
        # Wicks extend a random amount beyond the candle body
        high_price = candle_top    + random.uniform(0, WICK_EXTENSION)
        low_price  = candle_bottom - random.uniform(0, WICK_EXTENSION)
        low_price  = max(low_price, 0.01) # floor at near-zero
 
        opens.append(round(open_price, 2))
        closes.append(round(close_price, 2))
        highs.append(round(high_price, 2))
        lows.append(round(low_price, 2))
 
        current_price = close_price # next candle opens where this one closed
 
    print(f"Generated {len(dates)} OHLC data points.")
 
    # 2. Call the Tool Directly
    try:
        print("calling generate_candlestick_chart()...")
        image_result = generate_candlestick_chart(
            dates=dates,
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            symbol="TEST-CO",
            theme=random.choice(THEMES)
        )
 
        # 3. Save the output to verify visual correctness
        output_filename = "src/backend/charts/test_candlestick_output.png"
        with open(output_filename, "wb") as f:
            f.write(image_result.data)
 
        print(f"Success! Image saved to '{output_filename}'")
        print("Please open this file to verify candle colors, wicks, and styles.")
 
    except Exception as e:
        print(f"Error during generation: {e}")
 
 
if __name__ == "__main__":
    chart_generator = int(input("Please select which chart you want to test:" \
                            "\n\t(1) basic line chart\n\t(2) advanced line chart\n\t(3) candlestick chart\n> "))
    match chart_generator:
        case 1:
            test_chart_generation(advanced=False)
        case 2:
            test_chart_generation(advanced=True)
        case 3:
            test_candlestick_generation()