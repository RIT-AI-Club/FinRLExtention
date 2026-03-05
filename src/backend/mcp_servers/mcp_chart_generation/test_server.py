from server import *
from datetime import datetime, timedelta
import random

# NVIDIA Theme – "Neon Future"
# Inspired by NVIDIA's green-on-black aesthetic, futuristic and sleek.
NVIDIA_THEME = {
    # Primary line: glowing green
    "line": "#76B900",
    # Text: crisp white
    "text": "#FFFFFF",
    # Background: subtle gradient (simulated with a dark base)
    "background": "#0A0A0A",
    # Grid: faint green dots
    "grid": "#76B900",
    # Trend line: vibrant cyan
    "trend_line": "#00FF9D",
    "trend_line_style": "-.",
    # Annotation: high-tech terminal style
    "annotation_background": "#1E1E1E",
    "annotation_edge": "#76B900",
    "annotation_text": "#00FF9D",
    "annotation_font": "Courier New",   # (new) monospace for tech feel
    "arrowprops": dict(arrowstyle="->", color="#76B900", lw=1.5),  # (new) custom arrow
}

# AMD Theme – "Volcanic Energy"
# AMD’s red evokes power and speed; orange accents add dynamism.
AMD_THEME = {
    "line": "#ED1C24",
    "line_width": 2.5,
    "marker": "^",                       # triangular markers (pointing up)
    "marker_size": 7,
    "text": "#FFFFFF",
    "title_font": "Impact",              # strong, energetic
    "label_font": "Verdana",
    # Background: deep volcanic gradient
    "background": "#2E0A0A",              # dark red-brown
    "background_gradient": True,
    # Grid: orange embers
    "grid": "#FAA61A",
    "grid_style": "--",
    "grid_alpha": 0.4,
    # Trend line: golden yellow
    "trend_line": "#FFC72C",
    "trend_line_style": (0, (5, 1)),      # custom dash pattern
    # Annotation: fiery glow
    "annotation_background": "#FFD700",
    "annotation_edge": "#ED1C24",
    "annotation_text": "#000000",
    "annotation_font": "Arial Black",
    "arrowprops": dict(arrowstyle="fancy", color="#FAA61A", lw=2),
}

# META Theme – "Digital Horizon"
# Meta’s blue palette, clean and trustworthy, with a subtle gradient evoking the metaverse.
META_THEME = {
    "line": "#1877F2",
    "line_width": 2.2,
    "marker": "o",                       # circles – friendly and approachable
    "marker_size": 6,
    "text": "#1C1E21",                    # dark grey for readability on white
    "title_font": "Helvetica Neue",       # clean sans-serif
    "label_font": "Helvetica",
    # Background: clean white with faint blue gradient
    "background": "#FFFFFF",
    "background_gradient": "#E7F0FF",      # (new) light blue gradient suggestion
    # Grid: soft blue
    "grid": "#B0C4DE",
    "grid_style": "-.",
    "grid_alpha": 0.5,
    # Trend line: deeper blue
    "trend_line": "#0A4C8A",
    "trend_line_style": (0, (3, 1, 1, 1)), # custom pattern
    # Annotation: subtle blue box
    "annotation_background": "#E7F0FF",
    "annotation_edge": "#1877F2",
    "annotation_text": "#1C1E21",
    "annotation_font": "Helvetica",
    "arrowprops": dict(arrowstyle="->", color="#1877F2", lw=1),
}

# X Theme – "Dark Mode Edge"
# Bold black and white with electric blue accents, reflecting the platform’s edgy vibe.
X_THEME = {
    "line": "#FFFFFF",                     # white line on dark
    "line_width": 2.5,
    "marker": "s",                         # square markers – modern
    "marker_size": 5,
    "text": "#FFFFFF",
    "title_font": "Arial Black",
    "label_font": "Arial",
    # Background: deep black
    "background": "#000000",
    "background_gradient": False,
    # Grid: dark grey, almost invisible
    "grid": "#333333",
    "grid_style": ":",
    "grid_alpha": 0.2,
    # Trend line: electric blue
    "trend_line": "#1DA1F2",
    "trend_line_style": "--",
    # Annotation: high contrast with neon blue
    "annotation_background": "#111111",
    "annotation_edge": "#1DA1F2",
    "annotation_text": "#1DA1F2",
    "annotation_font": "Arial",
    "arrowprops": dict(arrowstyle="->", color="#1DA1F2", lw=1.5),
    # Marker edge and fill for extra style
    "marker_edge": "#1DA1F2",               # (new) outline for markers
    "marker_fill": "#FFFFFF",                # (new) fill color
}

THEMES = [NVIDIA_THEME, AMD_THEME, META_THEME, X_THEME]

START_PRICE = 76.12 # start price for dummy prices
PRICE_DEVIATION = 2.5 # how far a new price may deviate from the last price
NUMBER_OF_POINTS = 24 # number of price points (corresponds with date/time points)

def test_chart_generation(advanced):
    print("Starting local test of Stock Analyzer...")

    # 1. Simulate Data: Generate dummy stock data
    # This mimics the JSON arguments Gemini would pass to the tool
    base_date = datetime.now()
    # dates = [(base_date - timedelta(weeks=i)).isoformat() for i in range(52)] # 1-YEAR weekly trend
    # dates = [(base_date - timedelta(days=i)).isoformat() for i in range(30)] # 1-MONTH daily trend
    # dates = [(base_date - timedelta(days=i)).isoformat() for i in range(14)] # 2-WEEK daily trend
    # dates = [(base_date - timedelta(hours=i)).isoformat() for i in range(72)] #  3-DAY hourly trend
    dates = [(base_date - timedelta(hours=i)).isoformat() for i in range(24)] # 1-DAY hourly trend
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
    