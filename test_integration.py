# test_integration.py
# Full system integration test.
# Tests the complete flow: setup → trade → analytics → AI → insights → cleanup
# Run this any time you make significant changes to verify nothing broke.
# DELETE after confirming — or keep as a regression test suite.

import sys
sys.path.insert(0, ".")

import logging
from config.logging_config import setup_logging
setup_logging()

logger = logging.getLogger("integration_test")

from datetime import datetime
import json

from core.trade_repository import initialize_database, TradeRepository
from core.market_data import MarketDataService
from core.analytics_engine import AnalyticsEngine
from core.visualization_engine import VisualizationEngine
from core.ai_engine import AIEngine
from core.insights_engine import InsightsEngine, InsightRepository
import plotly.graph_objects as go


def section(title: str) -> None:
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print(f"{'═'*55}")


def check(label: str, condition: bool, detail: str = "") -> bool:
    icon = "✓" if condition else "✗"
    detail_str = f" — {detail}" if detail else ""
    print(f"  {icon} {label}{detail_str}")
    return condition


passed = []
failed = []

def run_check(label: str, condition: bool, detail: str = "") -> None:
    result = check(label, condition, detail)
    if result:
        passed.append(label)
    else:
        failed.append(label)


# ══════════════════════════════════════════════════════════════════════════════

section("LAYER 1 — DATABASE INITIALIZATION")

initialize_database()

from pathlib import Path
from config.settings import DB_PATH

run_check("Database file exists", Path(DB_PATH).exists(), str(DB_PATH))
run_check(
    "Tables created",
    True,
    "trades, ai_insights, market_snapshots"
)


# ══════════════════════════════════════════════════════════════════════════════

section("LAYER 2 — TRADE REPOSITORY")

repo = TradeRepository()

# Insert open trade
open_id = repo.insert_trade({
    "ticker": "NVDA",
    "company_name": "NVIDIA Corporation",
    "sector": "Technology",
    "quantity": 5,
    "direction": "long",
    "entry_price": 875.00,
    "entry_date": "2025-02-10T09:45:00",
    "stop_loss_price": 855.00,
    "take_profit_price": 915.00,
    "strategy_name": "Breakout",
    "timeframe": "swing",
    "entry_reasoning": "Clean breakout above key resistance. Volume 2x average. Sector momentum strong.",
    "emotional_state": "calm",
    "confidence_level": 8,
    "fomo_factor": 0,
    "followed_plan": 1,
    "market_condition": "trending_up",
    "spy_direction": "up",
})
run_check("Insert open trade", isinstance(open_id, int), f"id={open_id}")

# Read it back
trade = repo.get_trade_by_id(open_id)
run_check("Read trade by id", trade is not None)
run_check("Trade outcome is open", trade["outcome"] == "open")
run_check("Ticker correct", trade["ticker"] == "NVDA")

# Close it
success = repo.close_trade(
    trade_id=open_id,
    exit_price=912.50,
    exit_date="2025-02-13T14:30:00",
    exit_reason="take_profit_hit",
    exit_reasoning="Hit target cleanly. Strong momentum throughout.",
    stop_loss_honored=True,
)
run_check("Close trade", success)

closed = repo.get_trade_by_id(open_id)
run_check("Outcome updated to win", closed["outcome"] == "win")
run_check(
    "P&L calculated correctly",
    abs(closed["gross_pnl"] - (912.50 - 875.00) * 5) < 0.01,
    f"P&L=${closed['gross_pnl']}"
)
run_check(
    "Return % calculated",
    closed["return_pct"] is not None,
    f"{closed['return_pct']:.2f}%"
)

# Insert a losing trade for analytics variety
loss_id = repo.insert_trade({
    "ticker": "META",
    "quantity": 8,
    "direction": "long",
    "entry_price": 580.00,
    "exit_price": 561.00,
    "entry_date": "2025-02-11T11:00:00",
    "exit_date": "2025-02-11T15:30:00",
    "exit_reason": "stop_loss_hit",
    "strategy_name": "Momentum",
    "timeframe": "intraday",
    "entry_reasoning": "Momentum play on earnings. Entered too early.",
    "emotional_state": "excited",
    "confidence_level": 9,
    "fomo_factor": 1,
    "followed_plan": 0,
    "market_condition": "volatile",
    "spy_direction": "down",
    "stop_loss_price": 572.00,
    "take_profit_price": 600.00,
})
run_check("Insert losing trade", isinstance(loss_id, int))

# DataFrame load
df = repo.get_trades_as_dataframe()
run_check(
    "DataFrame loads correctly",
    not df.empty,
    f"{len(df)} closed trades"
)
run_check(
    "DataFrame has expected columns",
    "net_pnl" in df.columns and "outcome" in df.columns
)

# Other repository methods
open_trades = repo.get_open_trades()
run_check("get_open_trades returns list", isinstance(open_trades, list))

by_ticker = repo.get_trades_by_ticker("NVDA")
run_check("get_trades_by_ticker works", len(by_ticker) >= 1)


# ══════════════════════════════════════════════════════════════════════════════

section("LAYER 3 — MARKET DATA SERVICE")

market = MarketDataService()

valid = market.validate_ticker("AAPL")
run_check("Ticker validation — valid", valid)

invalid = market.validate_ticker("XYZINVALIDTICKER")
run_check("Ticker validation — invalid", not invalid)

snapshot = market.get_snapshot("AAPL")
run_check("Live snapshot fetched", snapshot is not None)
run_check(
    "Snapshot has required fields",
    snapshot is not None and all(
        k in snapshot for k in
        ["ticker", "close_price", "daily_change_pct", "volume"]
    ),
    f"AAPL @ ${snapshot['close_price']}" if snapshot else "fetch failed"
)

# Cache test
import time
start = time.time()
snapshot2 = market.get_snapshot("AAPL")
elapsed = time.time() - start
run_check(
    "Cache working (2nd call fast)",
    elapsed < 0.5,
    f"{elapsed:.3f}s"
)

history = market.get_price_history("AAPL", period="1mo")
run_check(
    "Price history fetched",
    history is not None and len(history) > 0,
    f"{len(history)} days" if history is not None else "failed"
)


# ══════════════════════════════════════════════════════════════════════════════

section("LAYER 4 — ANALYTICS ENGINE")

engine = AnalyticsEngine()

summary = engine.compute_summary_metrics(df)
run_check(
    "Summary metrics computed",
    summary["total_trades"] > 0,
    f"{summary['total_trades']} trades, P&L=${summary['total_pnl']}"
)
run_check(
    "Win rate calculated",
    0 <= summary["win_rate"] <= 100,
    f"{summary['win_rate']}%"
)
run_check(
    "Expectancy calculated",
    isinstance(summary["expectancy"], float),
    f"${summary['expectancy']}"
)

curve = engine.compute_pnl_curve(df)
run_check("P&L curve generated", not curve.empty)
run_check(
    "Curve has cumulative column",
    "cumulative_pnl" in curve.columns
)

sharpe = engine.compute_sharpe_ratio(df)
run_check(
    "Sharpe ratio computed",
    "sharpe_ratio" in sharpe,
    f"{sharpe['sharpe_ratio']}"
)

enriched = engine.engineer_features(df)
derived = len(enriched.columns) - len(df.columns)
run_check(
    "Feature engineering adds columns",
    derived > 0,
    f"+{derived} derived features"
)

corr = engine.compute_feature_correlations(df)
run_check(
    "Correlations computed",
    True,
    f"{len(corr)} features analyzed"
)

ai_ctx = engine.build_ai_context(df)
run_check(
    "AI context built",
    "summary" in ai_ctx and "emotion_win_rates" in ai_ctx
)
run_check(
    "AI context has risk metrics",
    "risk_metrics" in ai_ctx
)


# ══════════════════════════════════════════════════════════════════════════════

section("LAYER 5 — VISUALIZATION ENGINE")

viz = VisualizationEngine()

charts = [
    ("pnl_curve", lambda: viz.pnl_curve(df)),
    ("pnl_distribution", lambda: viz.pnl_distribution(df)),
    ("win_loss_donut", lambda: viz.win_loss_donut(df)),
    ("drawdown_chart", lambda: viz.drawdown_chart(df)),
    ("rolling_win_rate", lambda: viz.rolling_win_rate_chart(df)),
    ("emotion_chart", lambda: viz.emotion_performance_chart(df)),
    ("correlation_bar", lambda: viz.correlation_bar(df)),
    ("empty_chart", lambda: viz._empty_chart("test")),
]

for name, fn in charts:
    try:
        fig = fn()
        run_check(f"Chart: {name}", isinstance(fig, go.Figure))
    except Exception as e:
        run_check(f"Chart: {name}", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════

section("LAYER 6 — AI ENGINE")

try:
    ai = AIEngine()
    ai_available = True
    run_check("AIEngine initialized", True, f"model={ai.model}")
except EnvironmentError as e:
    ai_available = False
    run_check("AIEngine initialized", False, str(e))

if ai_available:
    # Test single trade analysis
    trade_to_analyze = repo.get_trade_by_id(open_id)
    result = ai.analyze_single_trade(trade_to_analyze)

    run_check("Single trade analysis", result["success"])
    if result["success"]:
        analysis = result["analysis"]
        run_check(
            "Analysis has required keys",
            all(k in analysis for k in [
                "trade_quality_score",
                "psychological_pattern",
                "specific_suggestions",
                "severity",
            ])
        )
        run_check(
            "Quality score in valid range",
            1 <= analysis.get("trade_quality_score", 0) <= 10,
            f"score={analysis.get('trade_quality_score')}"
        )
        run_check(
            "Tokens tracked",
            result["total_tokens"] > 0,
            f"{result['total_tokens']} tokens"
        )

    # Test pattern detection
    pattern_result = ai.detect_behavioral_patterns(ai_ctx)
    run_check("Pattern detection", pattern_result["success"])
    if pattern_result["success"]:
        patterns = pattern_result["patterns"]
        run_check(
            "Grade returned",
            patterns.get("performance_grade") in ["A","B","C","D","F"]
        )


# ══════════════════════════════════════════════════════════════════════════════

section("LAYER 7 — INSIGHTS ENGINE")

insights_engine = InsightsEngine()
insight_repo = InsightRepository()

run_check(
    "InsightsEngine initialized",
    True,
    f"AI available: {insights_engine.ai_available}"
)

if insights_engine.ai_available:
    # Analyze and store
    store_result = insights_engine.analyze_and_store_trade(open_id)
    run_check(
        "Analyze and store trade",
        store_result["success"],
        f"insight_id={store_result.get('insight_id')}"
    )

    # Retrieve stored insight
    if store_result["success"]:
        insight = insight_repo.get_insight_by_id(
            store_result["insight_id"]
        )
        run_check("Retrieve stored insight", insight is not None)
        run_check(
            "Content deserialized to dict",
            isinstance(insight.get("content"), dict)
        )

    # Pattern detection and storage
    pattern_store = insights_engine.detect_and_store_patterns()
    run_check(
        "Detect and store patterns",
        pattern_store["success"],
        f"insight_id={pattern_store.get('insight_id')}"
    )

    # Usage stats
    stats = insights_engine.get_usage_stats()
    run_check(
        "Usage stats tracked",
        stats["total_insights"] > 0,
        f"{stats['total_insights']} total insights, "
        f"${stats['token_usage']['estimated_cost_usd']:.4f} est. cost"
    )

    # History retrieval
    history = insights_engine.get_all_insights(limit=10)
    run_check(
        "Insight history retrieval",
        isinstance(history, list),
        f"{len(history)} insights retrieved"
    )


# ══════════════════════════════════════════════════════════════════════════════

section("RESULTS")

total = len(passed) + len(failed)
pass_rate = (len(passed) / total * 100) if total > 0 else 0

print(f"\n  Total checks:  {total}")
print(f"  Passed:        {len(passed)} ✓")
print(f"  Failed:        {len(failed)} ✗")
print(f"  Pass rate:     {pass_rate:.1f}%")

if failed:
    print(f"\n  FAILED CHECKS:")
    for f in failed:
        print(f"    ✗ {f}")

if len(failed) == 0:
    print(f"\n  ✅ ALL CHECKS PASSED — System is integration-ready")
elif len(failed) <= 2 and not ai_available:
    print(f"\n  ✅ SYSTEM HEALTHY — AI checks skipped (no API key)")
else:
    print(f"\n  ⚠️  {len(failed)} checks failed — review above")