from server import generate_financial_line_chart
from datetime import datetime, timedelta
import random

def test_chart_generation():
    print("Starting local test of Stock Analyzer...")

    # 1. Simulate Data: Generate 30 days of dummy stock data
    # This mimics the JSON arguments Gemini would pass to the tool
    base_date = datetime.now()
    dates = [(base_date - timedelta(days=i)).date().isoformat() for i in range(30)]
    dates.reverse() # Sort chronologically

    # create a random walk for prices
    prices = [150.0]
    for _ in range(29):
        change = random.uniform(-5, 5)
        prices.append(prices[-1] + change)

    print(f"Generated {len(dates)} days of sample data.")

    # 2. Call the Tool Directly
    try:
        print("calling generate_financial_line_chart()...")
        image_result = generate_financial_line_chart(dates=dates, prices=prices, symbol="TEST-CO")
        
        # 3. Save the output to verify visual correctness
        output_filename = "src/backend/charts/test_chart_output.png"
        with open(output_filename, "wb") as f:
            f.write(image_result.data)
            
        print(f"Success! Image saved to '{output_filename}'")
        print("Please open this file to verify the layout, dates, and styles.")

    except Exception as e:
        print(f"Error during generation: {e}")

if __name__ == "__main__":
    test_chart_generation()