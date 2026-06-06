import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from datetime import datetime, timedelta

from core.trade_repository import TradeRepository
from core.insights_engine import InsightsEngine
from app.utils import load_trades_df, render_sidebar

st.set_page_config(
    page_title="AI Insights — AI Trading Journal",
    page_icon="🤖",
    layout="wide",
)

render_sidebar()
st.title("🤖 AI Insights")
st.caption("Behavioral analysis and coaching powered by GPT-4o")
st.divider()

df = load_trades_df()
repo = TradeRepository()

if df.empty:
    st.info("No closed trades yet. Log and close trades to unlock AI analysis.")
    st.stop()

try:
    engine = InsightsEngine()
    ai_available = engine.ai_available
except Exception as e:
    st.error(f"InsightsEngine failed to initialize: {e}")
    st.stop()

if not ai_available:
    st.error(
        "OpenAI API key not found. "
        "Add OPENAI_API_KEY to your .env file to enable AI features."
    )
    st.stop()

usage = engine.get_usage_stats()
token_data = usage["token_usage"]

uc1, uc2, uc3, uc4 = st.columns(4)
with uc1:
    st.metric("Total Insights", usage["total_insights"])
with uc2:
    st.metric(
        "Total Tokens Used",
        f"{token_data['total_all']:,}"
    )
with uc3:
    st.metric(
        "Est. API Cost",
        f"${token_data['estimated_cost_usd']:.4f}"
    )
with uc4:
    st.metric(
        "Trades Analyzed",
        usage["by_type"].get("trade_analysis", 0)
    )

st.divider()

if df.empty:
    st.info("No closed trades yet. Log and close trades to unlock AI analysis.")
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "🔍 Trade Analysis",
    "📊 Pattern Detection",
    "📅 Weekly Review",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SINGLE TRADE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    col_gen, col_hist = st.columns([1.5, 1])

    with col_gen:
        st.markdown("#### Analyze a Trade")

    # Build trade selector options
        all_trades = repo.get_all_trades(closed_only=True)

        if not all_trades:
            st.info("No closed trades available for analysis.")
        else:
            # Build dropdown options
            trade_options = {}
            for t in all_trades:
                entry_dt = datetime.fromisoformat(t["entry_date"])
                icon = "✅" if t["outcome"] == "win" else "❌"
                label = (
                    f"{icon} {t['ticker']} — "
                    f"${t.get('net_pnl', 0):+.2f} | "
                    f"{entry_dt.strftime('%b %d')}"
                )
                trade_options[label] = t["id"]

            selected_label = st.selectbox(
                "Select Trade",
                options=list(trade_options.keys()),
            )
            selected_id = trade_options[selected_label]

            analyze_btn = st.button(
                "🤖 Analyze Trade",
                type="primary",
            )

            if analyze_btn:
                with st.spinner("AI is analyzing..."):
                    result = engine.analyze_and_store_trade(selected_id)

                if result["success"]:
                    analysis = result["analysis"]
                    score = analysis.get("trade_quality_score", 0)
                    severity = analysis.get("severity", "")

                    severity_icons = {
                        "positive": "🟢",
                        "minor_issue": "🟡",
                        "significant_issue": "🟠",
                        "critical_issue": "🔴",
                    }
                    icon = severity_icons.get(severity, "⚪")

                    st.markdown(
                        f"**Trade Quality: {score}/10** "
                        f"{icon} {severity.replace('_', ' ').title()}"
                    )
                    st.divider()

                    st.markdown("**Psychological Pattern**")
                    st.info(analysis.get("psychological_pattern", "—"))

                    ac1, ac2 = st.columns(2)
                    with ac1:
                        st.markdown("**What Went Well**")
                        st.success(analysis.get("what_went_well", "—"))
                    with ac2:
                        st.markdown("**Primary Mistake**")
                        mistake = analysis.get("primary_mistake", "None")
                        if mistake and mistake != "None":
                            st.warning(mistake)
                        else:
                            st.success("No significant mistakes")

                    st.markdown("**Risk Management**")
                    st.info(analysis.get("risk_management_assessment", "—"))

                    st.markdown("**Root Cause**")
                    st.info(analysis.get("root_cause", "—"))

                    st.markdown("**Suggestions**")
                    for i, s in enumerate(
                        analysis.get("specific_suggestions", []), 1
                    ):
                        st.markdown(f"**{i}.** {s}")

                    st.caption(
                        f"Tokens: {result['total_tokens']} | "
                        f"Saved as insight #{result['insight_id']}"
                    )
                else:
                    st.error(f"Analysis failed: {result['error']}")

    with col_hist:
        st.markdown("#### Past Analyses")

        past = engine.get_all_insights(limit=20)
        trade_analyses = [
            i for i in past
            if i.get("insight_type") == "trade_analysis"
        ]

        if not trade_analyses:
            st.caption("No past analyses yet.")
        else:
            for insight in trade_analyses[:8]:
                content = insight.get("content", {})
                score = content.get("trade_quality_score", "?")
                severity = content.get("severity", "")
                ticker = insight.get("ticker", "Unknown")
                outcome = insight.get("outcome", "")
                created = insight.get("created_at", "")[:10]
                pnl = insight.get("net_pnl")

                outcome_icon = "✅" if outcome == "win" else "❌"
                severity_short = {
                    "positive": "🟢",
                    "minor_issue": "🟡",
                    "significant_issue": "🟠",
                    "critical_issue": "🔴",
                }.get(severity, "⚪")

                with st.expander(
                    f"{outcome_icon} {ticker} | "
                    f"Score: {score}/10 {severity_short} | "
                    f"{created}"
                ):
                    pattern = content.get(
                        "psychological_pattern", "—"
                    )
                    st.caption(f"**Pattern:** {pattern}")

                    if pnl is not None:
                        pnl_color = "🟢" if pnl >= 0 else "🔴"
                        st.caption(f"**P&L:** {pnl_color} ${pnl:+.2f}")

                    top_suggestion = content.get(
                        "specific_suggestions", ["—"]
                    )
                    if top_suggestion:
                        st.caption(
                            f"**Top suggestion:** {top_suggestion[0]}"
                        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PATTERN DETECTION
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    col_new, col_old = st.columns([1.5, 1])

    # ── Left: Generate new pattern analysis ───────────────────────────────────
    with col_new:
        st.markdown("#### Detect Behavioral Patterns")
        st.caption(
            f"Analyzes all {len(df)} closed trades for "
            "systematic behavioral biases."
        )

        pattern_btn = st.button(
            "🔍 Detect My Patterns",
            type="primary",
        )

        if pattern_btn:
            with st.spinner(
                "Analyzing your complete trading history... "
                "15-20 seconds."
            ):
                result = engine.detect_and_store_patterns()

            if result["success"]:
                patterns = result["patterns"]

                grade = patterns.get("performance_grade", "?")
                grade_icon = {
                    "A": "🟢", "B": "🟢",
                    "C": "🟡", "D": "🟠", "F": "🔴"
                }.get(grade, "⚪")

                pc1, pc2 = st.columns([1, 3])
                with pc1:
                    st.metric(
                        "Performance Grade",
                        f"{grade_icon} {grade}"
                    )
                with pc2:
                    st.markdown(
                        f"**{patterns.get('overall_assessment', '—')}**"
                    )

                st.divider()

                # Critical patterns
                critical = patterns.get("critical_patterns", [])
                if critical:
                    st.markdown("**Critical Patterns**")
                    for i, pattern in enumerate(critical, 1):
                        with st.expander(
                            f"Pattern {i}: "
                            f"{pattern.get('pattern_name', 'Unknown')}",
                            expanded=(i == 1),
                        ):
                            st.markdown("**Evidence**")
                            st.info(pattern.get("evidence", "—"))
                            st.markdown("**Financial Impact**")
                            st.warning(pattern.get("financial_impact", "—"))
                            st.markdown("**Correction**")
                            st.success(pattern.get("correction", "—"))

                # Strengths
                strengths = patterns.get("strengths", [])
                if strengths:
                    st.markdown("**Your Strengths**")
                    for s in strengths:
                        st.success(f"✅ {s}")

                st.divider()
                st.markdown("**🎯 Top Priority Action**")
                st.error(patterns.get("top_priority_action", "—"))
                st.info(
                    f"**Estimated improvement:** "
                    f"{patterns.get('estimated_improvement', '—')}"
                )

                st.caption(
                    f"Tokens: {result['total_tokens']} | "
                    f"Trades analyzed: {result['trades_analyzed']} | "
                    f"Saved as insight #{result['insight_id']}"
                )
            else:
                st.error(f"Pattern detection failed: {result['error']}")

    # ── Right: History ─────────────────────────────────────────────────────────
    with col_old:
        st.markdown("#### Pattern History")

        history = engine.get_pattern_history(limit=5)

        if not history:
            st.caption("No pattern analyses yet.")
        else:
            for insight in history:
                content = insight.get("content", {})
                grade = content.get("performance_grade", "?")
                created = insight.get("created_at", "")[:10]
                assessment = content.get("overall_assessment", "—")

                grade_icon = {
                    "A": "🟢", "B": "🟢",
                    "C": "🟡", "D": "🟠", "F": "🔴"
                }.get(grade, "⚪")

                with st.expander(
                    f"Grade: {grade_icon} {grade} | {created}"
                ):
                    st.caption(assessment[:120] + "...")
                    patterns = content.get("critical_patterns", [])
                    if patterns:
                        st.caption(
                            f"Top pattern: "
                            f"{patterns[0].get('pattern_name', '—')}"
                        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WEEKLY REVIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    col_new2, col_old2 = st.columns([1.5, 1])

    # ── Left: Generate new weekly summary ─────────────────────────────────────
    with col_new2:
        st.markdown("#### Generate Weekly Review")

        days_back = st.slider(
            "Days to include",
            min_value=3,
            max_value=30,
            value=7,
            help="Generate review for the past N days of trades"
        )

        weekly_btn = st.button(
            "📅 Generate Review",
            type="primary",
        )

        if weekly_btn:
            with st.spinner("Generating weekly review..."):
                result = engine.generate_and_store_weekly_summary(
                    days_back=days_back
                )

            if result["success"]:
                summary = result["summary"]

                grade = summary.get("week_grade", "?")
                grade_icon = {
                    "A": "🟢", "B": "🟢",
                    "C": "🟡", "D": "🟠", "F": "🔴"
                }.get(grade, "⚪")

                wc1, wc2 = st.columns([1, 4])
                with wc1:
                    st.metric(
                        "Week Grade",
                        f"{grade_icon} {grade}"
                    )
                with wc2:
                    st.markdown(
                        f"**{summary.get('headline', '—')}**"
                    )

                st.divider()

                st.markdown("**Performance Narrative**")
                st.markdown(summary.get("performance_narrative", "—"))

                st.divider()

                wc3, wc4 = st.columns(2)
                with wc3:
                    st.markdown("**🏆 Best Moment**")
                    st.success(summary.get("best_moment", "—"))
                    st.markdown("**😌 Emotional Pattern**")
                    st.info(summary.get("emotional_pattern", "—"))
                with wc4:
                    st.markdown("**📚 Learning Moment**")
                    st.warning(summary.get("learning_moment", "—"))
                    st.markdown("**🎯 Focus for Next Week**")
                    st.error(summary.get("focus_for_next_week", "—"))

                st.caption(
                    f"Trades reviewed: {result['trade_count']} | "
                    f"Tokens: {result['total_tokens']} | "
                    f"Saved as insight #{result['insight_id']}"
                )
            else:
                st.error(f"Weekly review failed: {result['error']}")

    # ── Right: History ─────────────────────────────────────────────────────────
    with col_old2:
        st.markdown("#### Past Reviews")

        weekly_history = engine.get_weekly_summary_history(limit=5)

        if not weekly_history:
            st.caption("No weekly reviews yet.")
        else:
            for insight in weekly_history:
                content = insight.get("content", {})
                grade = content.get("week_grade", "?")
                headline = content.get("headline", "—")
                created = insight.get("created_at", "")[:10]

                grade_icon = {
                    "A": "🟢", "B": "🟢",
                    "C": "🟡", "D": "🟠", "F": "🔴"
                }.get(grade, "⚪")

                with st.expander(
                    f"{grade_icon} Grade {grade} | {created}"
                ):
                    st.caption(headline)
                    focus = content.get("focus_for_next_week", "—")
                    st.caption(f"Focus: {focus[:80]}...")
