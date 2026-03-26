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
NUMBER_OF_POINTS = 14 # number of price points (corresponds with date/time points)

def test_chart_generation(advanced):
    print("Starting local test of Stock Analyzer...")

    # 1. Simulate Data: Generate dummy stock data
    # This mimics the JSON arguments Gemini would pass to the tool
    base_date = datetime.now()
    dates = [(base_date - timedelta(weeks=i)).isoformat() for i in range(52)] # 1-YEAR weekly trend
    # dates = [(base_date - timedelta(days=i)).isoformat() for i in range(30)] # 1-MONTH daily trend
    dates = [(base_date - timedelta(days=i)).isoformat() for i in range(14)] # 2-WEEK daily trend
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

if __name__ == "__main__":
    chart_generator = int(input("Please select which chart you want to test:" \
                            "\n\t(1) basic line chart\n\t(2) advanced line chart\n> "))
    match chart_generator:
        case 1:
            test_chart_generation(advanced=False)
        case 2:
            test_chart_generation(advanced=True)
    