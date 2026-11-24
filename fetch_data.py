import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

ENDPOINTS = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "ZECUSDT", "HYPEUSDT", "TRXUSDT", "BNBUSDT", "WBTCUSDT", "PAXGUSDT", "ADAUSDT", "SUIUSDT", "AVAXUSDT", "NEARUSDT", "UNIUSDT", "DOGEUSDT", "LTCUSDT", "PEPEUSDT", "LINKUSDT", "DOTUSDT", "BCHUSDT", "HBARUSDT", "XLMUSDT", "AAVEUSDT", "ICPUSDT", "SHIBUSDT", "INJUSDT", "NEXOUSDT", "WLDUSDT", "FETUSDT", "FILUSDT", "STXUSDT"]
DAYS = 500   # daily candles wanted

def get_json(path):
    for base in ENDPOINTS:
        try:
            with urllib.request.urlopen(base + path, timeout=15) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            print(f"  {base} -> HTTP {e.code}")
        except Exception as e:
            print(f"  {base} -> error: {type(e).__name__}")
    return None

def fmt(x):
    if x < 0.01:
        return f"{x:.8f}"
    if x < 100:
        return f"{x:.4f}"
    return f"{x:.2f}"

def day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

# 1. latest prices (one request for all coins)
data = get_json("/api/v3/ticker/price")
if not data:
    print("Could not fetch prices")
    sys.exit(1)
prices = {d["symbol"]: float(d["price"]) for d in data}

# 2. daily history for each coin
rows, not_found, failed = [], [], []
for sym in SYMBOLS:
    if sym not in prices:
        not_found.append(sym)
        continue
    candles = get_json(f"/api/v3/klines?symbol={sym}&interval=1d&limit={DAYS}")
    if not candles:
        failed.append(sym)
        continue
    n = len(candles)
    status = "OK" if n >= DAYS else "NOT ENOUGH HISTORY"
    rows.append((sym, prices[sym], n, day(candles[0][0]), day(candles[-1][0]), status))
    time.sleep(0.1)

# 3. print the table
print(f"\nLatest price and up to {DAYS} days of daily history\n")
print(f"{'#':<4}{'pair':<11}{'latest price':>16}{'days':>7}  {'first day':<12}{'last day':<12}status")
for i, (sym, price, n, first, last, status) in enumerate(rows, 1):
    print(f"{i:<4}{sym:<11}{fmt(price):>16}{n:>7}  {first:<12}{last:<12}{status}")

short = [r for r in rows if r[5] != "OK"]
print(f"\n{len(rows)} pairs fetched, {len(rows) - len(short)} with full {DAYS} days, {len(short)} with not enough history")

if short:
    print("\nNOT ENOUGH HISTORY:")
    for sym, price, n, first, last, status in short:
        print(f"  {sym}: {n} days (listed {first})")
if not_found:
    print("\nNot found on Binance:")
    for s in not_found:
        print(f"  {s}")
if failed:
    print("\nCould not fetch candles (try again):")
    for s in failed:
        print(f"  {s}")
