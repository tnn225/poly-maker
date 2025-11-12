import websocket
import json
from datetime import datetime
from collections import deque
import numpy as np
from scipy.stats import norm
import csv
import os
import time

# === WebSocket endpoint ===
WS_URL = "wss://ws-live-data.polymarket.com"

# === Estimator parameters ===
CANDLE_LENGTH = 900  # 15 minutes
VOL_WINDOW = 10000     # seconds

# === Data storage ===
P_open = None
candle_start = None
prices = deque(maxlen=VOL_WINDOW)  # last N prices

# === Functions ===
def estimate_sigma(price_list):
    if len(price_list) < 2:
        return 0.0
    log_returns = np.diff(np.log(price_list))
    return np.std(log_returns)

def prob_btc_up(P_open, P_now, seconds_left, sigma, mu=0):
    if seconds_left <= 0 or sigma == 0:
        return float(P_now >= P_open)
    z = (np.log(P_now / P_open) - (mu - 0.5 * sigma**2) * seconds_left) / (sigma * np.sqrt(seconds_left))
    return norm.cdf(z)

def write_price_to_csv(ts, price):
    # Determine current UTC date for filename
    date_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    filename = f"./chainlink/btc_price_{date_str}.csv"
    file_exists = os.path.isfile(filename)
    
    # Write header if file is new
    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "btc_price"])
        writer.writerow([f"{ts:.0f}", f"{price:.3f}"])

# === WebSocket callbacks ===
def on_open(ws):
    print("✅ Connected to Polymarket RTDS")
    subscribe_message = {
        "action": "subscribe",
        "subscriptions": [
            {
                "topic": "crypto_prices_chainlink",
                "type": "*",
                "filters": ""
            }
        ]
    }
    ws.send(json.dumps(subscribe_message))
    print("📡 Subscribed to BTC/USD")

def on_message(ws, message):
    global P_open, candle_start, prices

    if not message.strip():
        return
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return

    payload = data.get("payload")
    if payload and payload.get("symbol") == "btc/usd":
        ts = payload["timestamp"] / 1000
        price = payload["value"]
        prices.append(price)
        write_price_to_csv(ts, price)  # ✅ write to daily CSV

        now = datetime.utcfromtimestamp(ts)
        minute_block = (now.minute // 15) * 15
        current_candle_start = now.replace(minute=minute_block, second=0, microsecond=0)

        if candle_start != current_candle_start:
            P_open = price
            candle_start = current_candle_start
            prices.clear()
            prices.append(P_open)
            print(f"\n🕐 New candle {candle_start} | Open={P_open:.2f}")

        elapsed = (now - candle_start).total_seconds()
        seconds_left = max(0, CANDLE_LENGTH - elapsed)
        sigma = estimate_sigma(list(prices))
        p_up = prob_btc_up(P_open, price, seconds_left, sigma)

        delta = price - P_open
        delta_pct = delta / P_open * 100
        print(f"[{now:%H:%M:%S}] BTC={price:.2f} | Δ={delta:+.2f} ({delta_pct:+.3f}%) "
              f"| σ={sigma:.6f} | sec_left={int(seconds_left):4d} | ProbUp={p_up:5.3f}")

def on_error(ws, error):
    print("⚠️ WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("🔌 WebSocket closed:", close_status_code, close_msg)

if __name__ == "__main__":
    ws = websocket.WebSocketApp(WS_URL,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
