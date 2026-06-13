import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import setup_logging
setup_logging()

import streamlit as st
import pandas as pd

from core.trade_repository import initialize_database, TradeRepository
from core.analytics_engine import AnalyticsEngine
from core.visualization_engine import VisualizationEngine
from app.utils import load_trades_df, load_open_trades, render_sidebar, safe_render
from app.auth import require_auth, render_user_menu

st.set_page_config(
    page_title="AI Trading Journal",
    page_icon="📈",
    layout="wide",                      # Full browser width
    initial_sidebar_state="expanded",
)

initialize_database()

user = require_auth()
if not user:
    st.stop()

render_user_menu(user)
render_sidebar(user_id=user["id"])

st.session_state["current_user"] = user

st.title("📈 AI Trading Journal")
st.caption(f"Welcome back, {user['name']}")
st.divider()

df = load_trades_df(user_id=user["id"])
open_trades = load_open_trades(user_id=user["id"])

if df.empty and not open_trades:
    st.markdown("### 👋 Welcome to Your Trading Journal")
    st.markdown(
        "You haven't logged any trades yet. "
        "Head to **Trade Log** in the sidebar to begin."
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📝 **Log Trade**\nRecord your trades with full psychological context")
    with col2:
        st.info("📊 **Analytics**\nDiscover performance patterns across strategies")
    with col3:
        st.info("🤖 **AI Insights**\nGet personalized coaching from AI analysis")
    st.stop()

engine = AnalyticsEngine()
viz = VisualizationEngine()

metrics = engine.compute_summary_metrics(df)
risk = engine.compute_risk_metrics_summary(df)

# ── KPI Row 1 — Core Performance ──────────────────────────────────────────────
st.markdown("#### Performance Overview")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="Total P&L",
        value=f"${metrics['total_pnl']:+,.2f}",
        help="Net profit/loss across all closed trades",
    )
with c2:
    st.metric(
        label="Win Rate",
        value=f"{metrics['win_rate']:.1f}%",
        help="Percentage of trades that were profitable",
    )
with c3:
    st.metric(
        label="Total Trades",
        value=metrics["total_trades"],
        help="Number of closed positions",
    )
with c4:
    st.metric(
        label="Avg Trade P&L",
        value=f"${metrics['avg_trade_pnl']:+,.2f}",
        help="Average profit or loss per trade",
    )

# ── KPI Row 2 — Risk Metrics ──────────────────────────────────────────────────
c5, c6, c7, c8 = st.columns(4)

with c5:
    st.metric(
        label="Best Trade",
        value=f"${metrics['best_trade']:+,.2f}",
    )
with c6:
    st.metric(
        label="Worst Trade",
        value=f"${metrics['worst_trade']:+,.2f}",
    )
with c7:
    st.metric(
        label="Profit Factor",
        value=f"{metrics['profit_factor']:.2f}x",
        help="Gross profits / Gross losses. Target: above 1.5",
    )
with c8:
    st.metric(
        label="Sharpe Ratio",
        value=f"{risk['sharpe_ratio']:.2f}",
        help=risk["sharpe_interpretation"],
    )

st.divider()

# ── Equity Curve ───────────────────────────────────────────────────────────────
st.markdown("#### Equity Curve")
# use_container_width=True makes the chart fill its column width
safe_render(
    lambda: st.plotly_chart(viz.pnl_curve(df), width="stretch"),
    "P&L curve failed to render"
)

st.divider()

left, right = st.columns([1, 1.5])

with left:
    st.markdown("#### Trade Outcomes")
    safe_render(
    lambda: st.plotly_chart(viz.win_loss_donut(df), width="stretch"),
    " Win/Loss chart failed to render"
    )
    

with right:
    st.markdown("#### Recent Trades")
    recent = df.sort_values("entry_date", ascending=False).head(10)

    # Select and format display columns
    display = recent[[
        "ticker", "entry_date", "outcome",
        "net_pnl", "return_pct", "strategy_name", "emotional_state"
    ]].copy()

    display["entry_date"] = pd.to_datetime(
        display["entry_date"]
    ).dt.strftime("%b %d, %Y")

    display["net_pnl"] = display["net_pnl"].apply(
        lambda x: f"${x:+,.2f}" if pd.notna(x) else "-"
    )
    display["return_pct"] = display["return_pct"].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else "-"
    )

    display.columns = [
        "Ticker", "Date", "Outcome",
        "P&L", "Return", "Strategy", "Emotion"
    ]

    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
    )

if open_trades:
    st.divider()
    st.markdown(f"#### 🔄 Open Positions ({len(open_trades)})")

    open_df = pd.DataFrame(open_trades)
    cols_to_show = [
        c for c in
        ["ticker", "entry_price", "quantity", "entry_date", "strategy_name"]
        if c in open_df.columns
    ]

    open_df["entry_date"] = pd.to_datetime(
        open_df["entry_date"]
    ).dt.strftime("%b %d, %Y")

    st.dataframe(
        open_df[cols_to_show],
        width="stretch",
        hide_index=True,
    )