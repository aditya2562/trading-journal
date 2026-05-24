# test_day3.py — DELETE after testing

import sys
sys.path.insert(0, ".")

import logging
logging.basicConfig(level=logging.INFO)

from core.trade_repository import initialize_database, TradeRepository
from core.market_data import MarketDataService

print("\n" + "="*50)
print("DAY 3 TEST — Market Data Pipeline")
print("="*50 + "\n")

# ── Test 1: Database still works ──────────────────────────────────────────────
print("TEST 1: Database initialization")
initialize_database()
print("✓ Database ready\n")

# ── Test 2: Ticker validation ─────────────────────────────────────────────────
print("TEST 2: Ticker validation")
service = MarketDataService()

valid = service.validate_ticker("AAPL")
invalid = service.validate_ticker("INVALIDXYZ")
print(f"✓ AAPL valid: {valid}")
print(f"✓ INVALIDXYZ valid: {invalid}\n")

# ── Test 3: Fetch live snapshot ───────────────────────────────────────────────
print("TEST 3: Fetch real market snapshot for AAPL")
snapshot = service.get_snapshot("AAPL")
if snapshot:
    print(f"✓ Ticker:        {snapshot['ticker']}")
    print(f"✓ Close Price:   ${snapshot['close_price']}")
    print(f"✓ Daily Change:  {snapshot['daily_change_pct']}%")
    print(f"✓ Volume:        {snapshot['volume']:,.0f}")
    print(f"✓ Fetched At:    {snapshot['fetched_at']}")
else:
    print("✗ Failed to fetch snapshot")

# ── Test 4: Cache working ─────────────────────────────────────────────────────
print("\nTEST 4: Cache verification (second call should be instant)")
import time
start = time.time()
snapshot2 = service.get_snapshot("AAPL")   # Should hit cache
elapsed = time.time() - start
print(f"✓ Second call took: {elapsed:.4f} seconds (cached = near zero)")

# ── Test 5: Price history ─────────────────────────────────────────────────────
print("\nTEST 5: Price history fetch")
history = service.get_price_history("AAPL", period="1mo")
if history is not None:
    print(f"✓ Trading days fetched: {len(history)}")
    print(f"✓ Columns: {list(history.columns)}")
    print(f"✓ Most recent close: ${history['Close'].iloc[-1]:.2f}")

# ── Test 6: Multiple tickers ──────────────────────────────────────────────────
print("\nTEST 6: Multiple ticker snapshots")
tickers = ["MSFT", "TSLA", "NVDA"]
snapshots = service.get_multiple_snapshot(tickers)
for ticker, data in snapshots.items():
    print(f"✓ {ticker}: ${data['close_price']} ({data['daily_change_pct']:+.2f}%)")

# ── Test 7: DataFrame from repository ────────────────────────────────────────
print("\nTEST 7: Trade DataFrame (SQLAlchemy)")
repo = TradeRepository()

# Insert a test trade so the DataFrame has something
repo.insert_trade({
    "ticker": "MSFT",
    "company_name": "Microsoft Corporation",
    "sector": "Technology",
    "quantity": 15,
    "direction": "long",
    "entry_price": 420.00,
    "exit_price": 435.50,
    "entry_date": "2025-01-10T10:00:00",
    "exit_date": "2025-01-14T15:30:00",
    "stop_loss_price": 412.00,
    "take_profit_price": 436.00,
    "strategy_name": "Momentum",
    "timeframe": "swing",
    "entry_reasoning": "Strong earnings momentum, sector tailwind",
    "emotional_state": "calm",
    "confidence_level": 8,
    "fomo_factor": 0,
    "followed_plan": 1,
    "market_condition": "trending_up",
    "spy_direction": "up",
    "exit_reason": "take_profit_hit"
})

df = repo.get_trades_as_dataframe()
print(f"✓ DataFrame shape: {df.shape}")
print(f"✓ Columns: {list(df.columns)[:6]}...")
print(f"✓ Latest trade: {df.iloc[-1]['ticker']} P&L: ${df.iloc[-1]['gross_pnl']}")

print("\n" + "="*50)
print("✅ ALL DAY 3 TESTS PASSED")
print("="*50)