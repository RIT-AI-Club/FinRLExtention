"""
Run this program to test the chart generation MCP server.

Usage:
    python test_server.py                              # all charts, random theme & seed
    python test_server.py --theme nvidia --seed 42     # pin both for exact reproduction
    python test_server.py --theme amd --timespan 1y    # specific theme + timespan
    python test_server.py --charts 1 3                 # basic line + candlestick only
    python test_server.py --charts 2 --seed 7 --points 30

    # Run same data across all themes:
    for t in nvidia amd meta x; do
        python test_server.py --theme $t --seed 42
    done

Arguments:
    --charts    1=basic line, 2=advanced line, 3=candlestick (default: all)
    --theme     nvidia, amd, meta, x (default: random)
    --timespan  1y, 1mo, 3d, 1d, 1h (default: 3d)
    --seed      Integer for reproducible data (default: random)
    --points    Override number of data points (default: determined by --timespan)
"""

from server import *
from datetime import datetime, timedelta
import random
import argparse
import os
from example_themes import *

THEME_MAP = {
    "nvidia": NVIDIA_THEME,
    "amd":    AMD_THEME,
    "meta":   META_THEME,
    "x":      X_THEME,
}

START_PRICE = 150      # start price for dummy prices
PRICE_DEVIATION = 5    # how far a new price may deviate from the last price
NUMBER_OF_POINTS = 72  # number of price points (corresponds with date/time points)
WICK_EXTENSION = 1.5   # max extra range beyond open/close for high/low wicks

OUTPUT_DIR = "src/backend/charts"

TIMESPANS = {
    "1h":  (timedelta(minutes=1), 60),
    "1d":  (timedelta(hours=1),   24),
    "3d":  (timedelta(hours=1),   72),
    "2w": (timedelta(days=1),    14),
    "1mo": (timedelta(days=1),    30),
    "1y":  (timedelta(weeks=1),   52),
    "3y": (timedelta(weeks=1),    156),
    "6y": (timedelta(weeks=1),    312),
}


def make_prices(n, rng):
    prices = [START_PRICE]
    for _ in range(n - 1):
        new_price = max(0.01, prices[-1] + rng.uniform(-PRICE_DEVIATION, PRICE_DEVIATION))
        prices.append(new_price)
    return prices


def make_ohlc(n, rng):
    opens, highs, lows, closes = [], [], [], []
    current = START_PRICE
    for _ in range(n):
        open_p = current
        close_p = max(0.01, open_p + rng.uniform(-PRICE_DEVIATION, PRICE_DEVIATION))
        top, bot = max(open_p, close_p), min(open_p, close_p)
        opens.append(round(open_p, 2))
        closes.append(round(close_p, 2))
        highs.append(round(top + rng.uniform(0, WICK_EXTENSION), 2))
        lows.append(round(max(0.01, bot - rng.uniform(0, WICK_EXTENSION)), 2))
        current = close_p
    return opens, highs, lows, closes


def save_image(image_result, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(image_result.data)
    print(f"  Saved → {path}")


def test_line_chart(advanced, dates, rng, theme):
    label = "advanced line" if advanced else "basic line"
    print(f"\n[{label}] Generating...")
    prices = make_prices(len(dates), rng)
    try:
        result = generate_line_chart(
            dates=dates, prices=prices, symbol="TEST-CO",
            advanced=advanced, theme=theme
        )
        save_image(result, f"test_{'advanced' if advanced else 'basic'}_line.png")
    except Exception as e:
        print(f"  FAILED: {e}")


def test_candlestick_chart(dates, rng, theme):
    print("\n[candlestick] Generating...")
    opens, highs, lows, closes = make_ohlc(len(dates), rng)
    try:
        result = generate_candlestick_chart(
            dates=dates, opens=opens, highs=highs, lows=lows,
            closes=closes, symbol="TEST-CO", theme=theme
        )
        save_image(result, "test_candlestick.png")
    except Exception as e:
        print(f"  FAILED: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test chart generation")
    parser.add_argument(
        "--charts", nargs="+", type=int, choices=[1, 2, 3],
        default=[1, 2, 3],
        help="Charts to run: 1=basic line, 2=advanced line, 3=candlestick (default: all)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible output (default: random)"
    )
    parser.add_argument(
        "--timespan", choices=TIMESPANS.keys(), default="3d",
        help="Time span to simulate: 1h, 1d, 3d, 2w, 1mo, 1y, 3y, 6y (default: 3d)"
    )
    parser.add_argument(
        "--theme", choices=THEME_MAP.keys(), default=None,
        help="Theme to use: nvidia, amd, meta, x (default: random)"
    )
    parser.add_argument(
        "--points", type=int, default=None,
        help="Override number of data points (default: determined by --timespan)"
    )
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 9999)
    rng = random.Random(seed)
    print(f"Seed: {seed}  (re-run with --seed {seed} to reproduce)")

    theme = THEME_MAP[args.theme] if args.theme else rng.choice(list(THEME_MAP.values()))
    print(f"Theme: {args.theme or 'random'}")

    interval, default_points = TIMESPANS[args.timespan]
    n = args.points if args.points is not None else default_points
    base_date = datetime.now()
    dates = [(base_date - interval * i).isoformat() for i in range(n)]
    dates.reverse()

    for chart in sorted(set(args.charts)):
        if chart == 1:
            test_line_chart(advanced=False, dates=dates, rng=rng, theme=theme)
        elif chart == 2:
            test_line_chart(advanced=True, dates=dates, rng=rng, theme=theme)
        elif chart == 3:
            test_candlestick_chart(dates=dates, rng=rng, theme=theme)

    print("\nDone.")