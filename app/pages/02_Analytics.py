import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from core.analytics_engine import AnalyticsEngine
from core.visualization_engine import VisualizationEngine
from app.utils import load_trades_df, render_sidebar, safe_render

from app.auth import require_auth, render_user_menu

st.set_page_config(
    page_title="Analytics — AI Trading Journal",
    page_icon="📊",
    layout="wide",
)

user = require_auth()
if not user:
    st.stop()

render_user_menu(user)

render_sidebar(user_id=user["id"])
st.title("📊 Analytics")
st.caption("Pattern detection across your complete trade history")
st.divider()

df = load_trades_df(user_id=user["id"])

if df.empty:
    st.info("No closed trades yet. Log some trades to see analytics.")
    st.stop()

engine = AnalyticsEngine()
viz = VisualizationEngine()

# Total trade count context
st.caption(f"Analyzing {len(df)} closed trades")

# ── Five Analytics Tabs ────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Strategy",
    "🌍 Market",
    "📅 Time",
    "⚠️ Risk",
    "⚖️ R:R Discipline",
])


# ── TAB 1: Strategy Performance ───────────────────────────────────────────────
with tab1:
    st.markdown("#### Strategy Performance")
    st.caption(
        "Which strategies are actually working? "
        "Use this to stop trading strategies with negative edge."
    )

    strategy_df = engine.win_rate_by_strategy(df)

    if not strategy_df.empty:
        safe_render(
            lambda: st.plotly_chart(viz.performance_by_category(strategy_df,"strategy_name","Win Rate & Avg P&L by Strategy"), width="stretch"),
            "Performance Chart failed to render"
        )

        st.markdown("#### Strategy Summary Table")
        display = strategy_df.copy()
        display.columns = [
            c.replace("_", " ").title()
            for c in display.columns
        ]
        st.dataframe(display, width="stretch", hide_index=True)
    else:
        st.info("Log trades with strategy names to see this analysis.")


# ── TAB 2: Market Condition ────────────────────────────────────────────────────
with tab2:
    st.markdown("#### Performance by Market Condition")
    st.caption(
        "Does your strategy work in all market environments? "
        "Most strategies only work well in one type of market."
    )

    mc_df = engine.win_rate_by_market_condition(df)
    timeframe_df = engine.win_rate_by_timeframe(df)

    col_a, col_b = st.columns(2)

    with col_a:
        if not mc_df.empty:
            safe_render(
                lambda: st.plotly_chart(viz.performance_by_category(mc_df,"market_condition","Performance by Market Condition"), width="stretch"),
                "Chart failed to render"
            )
        else:
            st.info("Log market condition on trades to see this.")

    with col_b:
        if not timeframe_df.empty:
            safe_render(
                lambda: st.plotly_chart(viz.performance_by_category(timeframe_df,"timeframe","Performance by Timeframe"), width="stretch"),
                "Chart failed to render"
            )
        else:
            st.info("Log timeframe on trades to see this.")

    st.markdown("#### Monthly P&L")
    safe_render(
        lambda: st.plotly_chart(viz.monthly_pnl_bar(df), width="stretch"),
        "Monthly P&L chart failed to render"
    )


# ── TAB 3: Time Analysis ───────────────────────────────────────────────────────
with tab3:
    st.markdown("#### Performance by Day of Week")
    st.caption(
        "Are you systematically worse on certain days? "
        "This reveals behavioral patterns tied to market structure."
    )

    dow_df = engine.win_rate_by_day_of_week(df)

    if not dow_df.empty:
        safe_render(
            lambda: st.plotly_chart(viz.performance_by_category(dow_df,"day_of_week","Win Rate & Avg P&L by Day of Week"), width="stretch"),
            "Chart failed to render"
        )
    else:
        st.info("Need more trades to analyze day-of-week patterns.")

    st.markdown("#### Rolling Win Rate — Trend Over Time")
    st.caption(
        "Is your performance improving or deteriorating? "
        "A declining line means your edge is weakening."
    )
    safe_render(
        lambda: st.plotly_chart(viz.rolling_win_rate_chart(df), width="stretch"),
        "Rolling Win Rate chart failed to render"
    )


# ── TAB 4: Risk Analysis ───────────────────────────────────────────────────────
with tab4:
    st.markdown("#### Drawdown Analysis")
    st.caption(
        "How far did your account fall from its peak? "
        "Professional target: keep max drawdown below 20%."
    )

    # Risk metrics summary cards
    risk = engine.compute_risk_metrics_summary(df)

    rm1, rm2, rm3, rm4 = st.columns(4)
    with rm1:
        st.metric(
            "Max Drawdown",
            f"{risk['max_drawdown_pct']:.2f}%",
            help="Worst peak-to-trough decline"
        )
    with rm2:
        st.metric(
            "Max Drawdown $",
            f"${risk['max_drawdown_dollars']:,.2f}",
        )
    with rm3:
        st.metric(
            "Sharpe Ratio",
            f"{risk['sharpe_ratio']:.2f}",
            help=risk["sharpe_interpretation"],
        )
    with rm4:
        st.metric(
            "Calmar Ratio",
            f"{risk['calmar_ratio']:.2f}",
            help=risk["calmar_interpretation"],
        )

    safe_render(
        lambda: st.plotly_chart(viz.drawdown_chart(df), width="stretch"),
        "Drawdown chart failed to render"
    )

    st.markdown("#### P&L Distribution")
    st.caption(
        "Are your wins bigger than your losses? "
        "Ideal: loss distribution tight near zero, wins spread wide."
    )
    safe_render(
        lambda: st.plotly_chart(viz.pnl_distribution(df), width="stretch"),
        "P&L Distribution chart failed to render"
    )


# ── TAB 5: R:R Discipline ─────────────────────────────────────────────────────
with tab5:
    st.markdown("#### Risk:Reward Discipline")
    st.caption(
        "Are you executing trades as planned? "
        "Points below the diagonal = cutting winners early."
    )

    rr = engine.compute_rr_analysis(df)

    rr1, rr2, rr3 = st.columns(3)
    with rr1:
        st.metric(
            "Avg Planned R:R",
            f"{rr['avg_planned_rr']:.2f}:1",
        )
    with rr2:
        st.metric(
            "Avg Actual R:R",
            f"{rr['avg_actual_rr']:.2f}:1",
        )
    with rr3:
        st.metric(
            "Adherence Rate",
            f"{rr['rr_adherence_rate']:.1f}%",
            help="% of trades executed within 20% of planned R:R"
        )

    if rr["cutting_winners_early"]:
        st.warning(
            "⚠️ **Pattern Detected:** You are consistently closing winners before reaching your target. "
            "Your actual R:R is significantly below planned."
        )

    safe_render(
        lambda: st.plotly_chart(viz.rr_scatter(df), width="stretch"),
        "Reward Risk chart failed to render"
    )

    safe_render(
        lambda: st.plotly_chart(viz.correlation_bar(df), width="stretch"),
        "Correlation chart failed to render"
    )