import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

ENDPOINTS = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "ZECUSDT", "HYPEUSDT", "TRXUSDT", "BNBUSDT", "WBTCUSDT", "PAXGUSDT", "ADAUSDT", "SUIUSDT", "AVAXUSDT", "NEARUSDT", "UNIUSDT", "DOGEUSDT", "LTCUSDT", "PEPEUSDT", "LINKUSDT", "DOTUSDT", "BCHUSDT", "HBARUSDT", "XLMUSDT", "AAVEUSDT", "ICPUSDT", "SHIBUSDT", "INJUSDT", "NEXOUSDT", "WLDUSDT", "FETUSDT", "FILUSDT", "STXUSDT"]
LENGTH = 14          # TradingView default
DAYS = 100           # closed daily candles used
CHECK = "ETHUSDT"    # coin whose working is printed for checking

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

def true_ranges(candles):
    """candles = list of (high, low, close). First candle uses high - low."""
    tr = []
    for i, (h, l, c) in enumerate(candles):
        if i == 0:
            tr.append(h - l)
        else:
            pc = candles[i - 1][2]
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return tr

def atr_rma(tr, length):
    """Wilder's RMA: first value = average of first `length` TRs, then smoothed."""
    atr = sum(tr[:length]) / length
    out = [None] * (length - 1) + [atr]
    for t in tr[length:]:
        atr = (atr * (length - 1) + t) / length
        out.append(atr)
    return out

def fmt(x):
    if x < 0.01:
        return f"{x:.8f}"
    if x < 100:
        return f"{x:.4f}"
    return f"{x:.2f}"

def day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

data = get_json("/api/v3/ticker/price")
if not data:
    print("Could not fetch prices")
    sys.exit(1)
prices = {d["symbol"]: float(d["price"]) for d in data}

now_ms = int(time.time() * 1000)
rows, skipped, working = [], [], None

for sym in SYMBOLS:
    if sym not in prices:
        skipped.append(f"{sym}: not found on Binance")
        continue
    raw = get_json(f"/api/v3/klines?symbol={sym}&interval=1d&limit={DAYS + 1}")
    if not raw:
        skipped.append(f"{sym}: could not fetch candles (try again)")
        continue
    closed = [c for c in raw if c[6] < now_ms][-DAYS:]   # drop today's forming candle
    if len(closed) < DAYS:
        skipped.append(f"{sym}: NOT ENOUGH HISTORY ({len(closed)} closed days, needs {DAYS})")
        continue
    candles = [(float(c[2]), float(c[3]), float(c[4])) for c in closed]
    tr = true_ranges(candles)
    atr_series = atr_rma(tr, LENGTH)
    atr = atr_series[-1]
    price = prices[sym]
    rows.append((sym, price, atr, atr / price * 100, day(closed[-1][0])))
    if sym == CHECK:
        working = (closed, candles, tr, atr_series)
    time.sleep(0.1)

rows.sort(key=lambda r: r[3], reverse=True)    # highest ATR % first

print(f"\nDaily ATR ({LENGTH}, RMA) from {DAYS} closed candles, ranked by ATR % (highest first)")
print("ATR % = ATR / latest price x 100\n")
print(f"{'#':<4}{'pair':<11}{'latest price':>16}{'ATR':>16}{'ATR %':>9}  last candle")
for i, (sym, price, atr, pct, last) in enumerate(rows, 1):
    print(f"{i:<4}{sym:<11}{fmt(price):>16}{fmt(atr):>16}{pct:>8.2f}%  {last}")

if skipped:
    print("\nNot included:")
    for s in skipped:
        print("  " + s)

if working:
    closed, candles, tr, atr_series = working
    print(f"\nWorking for {CHECK} (last 5 closed days), to compare with TradingView:")
    print(f"{'date (UTC)':<12}{'high':>12}{'low':>12}{'prev close':>12}{'TR':>12}{'ATR 14':>12}")
    for i in range(len(candles) - 5, len(candles)):
        h, l, c = candles[i]
        print(f"{day(closed[i][0]):<12}{h:>12.2f}{l:>12.2f}{candles[i-1][2]:>12.2f}{tr[i]:>12.2f}{atr_series[i]:>12.2f}")
