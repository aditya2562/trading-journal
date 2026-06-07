import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from core.analytics_engine import AnalyticsEngine
from core.visualization_engine import VisualizationEngine
from app.utils import load_trades_df, render_sidebar, safe_render

st.set_page_config(
    page_title="Psychology — AI Trading Journal",
    page_icon="🧠",
    layout="wide",
)

render_sidebar()
st.title("🧠 Trading Psychology")
st.caption(
    "Behavioral finance analysis — understanding how your mental state drives your performance"
)
st.divider()

df = load_trades_df()

if df.empty:
    st.info(
        "No trade data yet. Log trades with emotional state and psychology fields to unlock behavioral analysis."
    )
    st.stop()

engine = AnalyticsEngine()
viz = VisualizationEngine()
psych = engine.compute_psychology_metrics(df)
behavioral = engine.compute_behavioral_correlations(df)

# ── Behavioral Findings Banner ─────────────────────────────────────────────────
# Show key findings at the top — most actionable insights first
if behavioral["findings"]:
    st.markdown("#### 🔍 Key Behavioral Findings")

    for finding in behavioral["findings"]:
        gap = finding.get("win_rate_gap", 0)

        if abs(gap) >= 20:
            # Large gap = significant finding = warning
            st.warning(f"⚠️ {finding['insight']}")
        elif abs(gap) >= 10:
            st.info(f"💡 {finding['insight']}")
        else:
            st.success(f"✅ {finding['insight']}")

    st.divider()

# ── Four Psychology Tabs ───────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "😌 Emotional State",
    "🚨 FOMO Analysis",
    "💪 Confidence",
    "📐 Correlations",
])

# ── TAB 1: Emotional State ────────────────────────────────────────────────────
with tab1:
    st.markdown("#### Win Rate by Emotional State")
    st.caption(
        "The most revealing chart in this system. "
        "If there's a large gap between calm and anxious win rates, "
        "your emotional state is your biggest edge — or biggest liability."
    )

    emotion_wr = psych["emotion_win_rates"]

    if not emotion_wr.empty:
        safe_render(
            lambda: st.plotly_chart(viz.emotion_performance_chart(df), width="stretch"),
            "Emotion performance chart failed to render"
        )

        st.markdown("#### Emotion Summary Table")
        display = emotion_wr.copy()
        display.columns = [
            c.replace("_", " ").title()
            for c in display.columns
        ]
        st.dataframe(display, width="stretch", hide_index=True)

        # Confidence by outcome
        conf = psych["avg_confidence_by_outcome"]
        if conf["avg_confidence_wins"] > 0:
            st.markdown("---")
            st.markdown("#### Confidence When Winning vs Losing")
            ca, cb = st.columns(2)
            with ca:
                st.metric(
                    "Avg Confidence on Wins",
                    f"{conf['avg_confidence_wins']:.1f}/10",
                )
            with cb:
                st.metric(
                    "Avg Confidence on Losses",
                    f"{conf['avg_confidence_losses']:.1f}/10",
                )

            if conf["avg_confidence_losses"] > conf["avg_confidence_wins"]:
                st.warning(
                    "⚠️ **Overconfidence Pattern:** You feel MORE confident "
                    "on losing trades than winning ones. "
                    "High confidence is not predicting success."
                )
    else:
        st.info("Log emotional state on your trades to see this analysis.")


# ── TAB 2: FOMO Analysis ──────────────────────────────────────────────────────
with tab2:
    st.markdown("#### FOMO vs Planned Trade Performance")
    st.caption(
        "FOMO (Fear Of Missing Out) trades are entered reactively — "
        "chasing a move already in progress. "
        "This chart quantifies exactly how much it costs you."
    )

    fomo = psych["fomo_impact"]

    if fomo["fomo_trade_count"] > 0 or fomo["non_fomo_trade_count"] > 0:
        fa, fb, fc = st.columns(3)
        with fa:
            st.metric("FOMO Trades", fomo["fomo_trade_count"])
        with fb:
            st.metric("Planned Trades", fomo["non_fomo_trade_count"])
        with fc:
            cost = fomo.get("fomo_cost", 0)
            st.metric(
                "Cost of FOMO (per trade)",
                f"${cost:+,.2f}",
                help="Difference in avg P&L between planned and FOMO trades"
            )

        safe_render(
            lambda: st.plotly_chart(viz.fomo_impact_chart(df), width="stretch"),
            "FOMO Impact chart failed to render"
        )

        if fomo["fomo_win_rate"] < fomo["non_fomo_win_rate"] - 15:
            st.error(
                f"🚨 **Critical Pattern:** FOMO trades win "
                f"{fomo['fomo_win_rate']:.1f}% vs "
                f"{fomo['non_fomo_win_rate']:.1f}% for planned trades. "
                f"Eliminating FOMO trades could significantly improve performance."
            )
    else:
        st.info("Log FOMO factor on trades to see this analysis.")


# ── TAB 3: Confidence ────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### Confidence Level vs Outcome")
    st.caption(
        "Is your confidence actually predictive? "
        "If the loss bars are taller at high confidence levels, "
        "you have a classic overconfidence problem."
    )

    safe_render(
        lambda: st.plotly_chart(viz.confidence_vs_outcome(df), width="stretch"),
        "Confidence chart failed to render"
    )

    st.markdown("#### Plan Adherence Impact")
    plan = psych["plan_adherence_impact"]

    if plan["planned_trade_count"] > 0:
        pa, pb = st.columns(2)
        with pa:
            st.metric(
                "Planned Trade Win Rate",
                f"{plan['planned_win_rate']:.1f}%",
                help=f"{plan['planned_trade_count']} trades"
            )
            st.metric(
                "Planned Avg P&L",
                f"${plan['planned_avg_pnl']:+,.2f}",
            )
        with pb:
            st.metric(
                "Unplanned Trade Win Rate",
                f"{plan['unplanned_win_rate']:.1f}%",
                help=f"{plan['unplanned_trade_count']} trades"
            )
            st.metric(
                "Unplanned Avg P&L",
                f"${plan['unplanned_avg_pnl']:+,.2f}",
            )

        gap = plan["planned_win_rate"] - plan["unplanned_win_rate"]
        if gap > 15:
            st.success(
                f"✅ Following your plan improves win rate by "
                f"{gap:.1f} percentage points."
            )
        elif gap < -5:
            st.warning(
                "Your plans may need refinement — "
                "unplanned trades are currently outperforming."
            )


# ── TAB 4: Correlations ──────────────────────────────────────────────────────
with tab4:
    st.markdown("#### Feature Correlations with Return %")
    st.caption(
        "Which behavioral factors most strongly predict whether "
        "a trade will be profitable? "
        "Positive (green) helps. Negative (red) hurts."
    )

    if behavioral.get("most_predictive_feature"):
        feature_clean = behavioral['most_predictive_feature'].replace("_", " ").title()
        st.info(
            f"🎯 **Most predictive factor:** {feature_clean} "
            f"(correlation: {behavioral['top_correlation']:+.3f})"
        )

    safe_render(
        lambda: st.plotly_chart(viz.correlation_bar(df), width="stretch"),
        "Correlation chart failed to render"
    )

    if behavioral["findings"]:
        st.markdown("#### Detailed Behavioral Findings")
        for finding in behavioral["findings"]:
            with st.expander(finding["label"]):
                if "impulsive_win_rate" in finding:
                    col_x, col_y = st.columns(2)
                    with col_x:
                        st.metric(
                            "Impulsive Win Rate",
                            f"{finding['impulsive_win_rate']}%"
                        )
                        st.metric(
                            "Impulsive Avg P&L",
                            f"${finding['impulsive_avg_pnl']:+,.2f}"
                        )
                    with col_y:
                        st.metric(
                            "Disciplined Win Rate",
                            f"{finding['disciplined_win_rate']}%"
                        )
                        st.metric(
                            "Disciplined Avg P&L",
                            f"${finding['disciplined_avg_pnl']:+,.2f}"
                        )
                st.caption(finding["insight"])