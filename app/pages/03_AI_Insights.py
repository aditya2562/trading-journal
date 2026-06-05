import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import json
from datetime import datetime, timedelta

from core.trade_repository import TradeRepository
from core.analytics_engine import AnalyticsEngine
from core.ai_engine import AIEngine
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
analytics = AnalyticsEngine()

if df.empty:
    st.info("No closed trades yet. Log and close trades to unlock AI analysis.")
    st.stop()

try:
    ai = AIEngine()
    ai_available = True
except EnvironmentError as e:
    st.error(f"AI Engine not available: {e}")
    ai_available = False
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "🔍 Single Trade Analysis",
    "📊 Pattern Detection",
    "📅 Weekly Review",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SINGLE TRADE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("#### Analyze Individual Trade")
    st.caption(
        "Select any closed trade for deep AI analysis — "
        "psychological patterns, risk management assessment, "
        "and specific improvement suggestions."
    )

    # Build trade selector options
    all_trades = repo.get_all_trades(closed_only=True)

    if not all_trades:
        st.info("No closed trades available for analysis.")
    else:
        trade_options = {}
        for t in all_trades:
            entry_dt = datetime.fromisoformat(t["entry_date"])
            outcome_icon = "✅" if t["outcome"] == "win" else "❌"
            label = (
                f"{outcome_icon} {t['ticker']} — "
                f"${t.get('net_pnl', 0):+.2f} | "
                f"{entry_dt.strftime('%b %d, %Y')} | "
                f"{t.get('strategy_name') or 'No strategy'}"
            )
            trade_options[label] = t["id"]

        selected_label = st.selectbox(
            "Select Trade to Analyze",
            options=list(trade_options.keys()),
        )

        selected_id = trade_options[selected_label]
        selected_trade = repo.get_trade_by_id(selected_id)

        # Show trade summary before analysis
        with st.expander("Trade Summary", expanded=False):
            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                st.metric("Ticker", selected_trade["ticker"])
                st.metric("Outcome", selected_trade["outcome"].upper())
            with tc2:
                st.metric("P&L", f"${selected_trade.get('net_pnl', 0):+.2f}")
                st.metric("Return", f"{selected_trade.get('return_pct', 0):+.2f}%")
            with tc3:
                st.metric(
                    "Emotion",
                    selected_trade.get("emotional_state") or "—"
                )
                st.metric(
                    "Confidence",
                    f"{selected_trade.get('confidence_level') or '—'}/10"
                )
            with tc4:
                st.metric(
                    "FOMO",
                    "Yes 🚨" if selected_trade.get("fomo_factor") else "No ✅"
                )
                st.metric(
                    "Followed Plan",
                    "Yes ✅" if selected_trade.get("followed_plan") else "No ❌"
                )

        analyze_btn = st.button(
            "🤖 Analyze This Trade",
            type="primary",
            use_container_width=False,
        )

        if analyze_btn:
            with st.spinner("AI is analyzing your trade..."):
                result = ai.analyze_single_trade(selected_trade)

            if not result["success"]:
                st.error(f"Analysis failed: {result['error']}")
            else:
                analysis = result["analysis"]

                # ── Score and severity header ──────────────────────────────────
                score = analysis.get("trade_quality_score", 0)
                severity = analysis.get("severity", "minor_issue")

                severity_colors = {
                    "positive": "🟢",
                    "minor_issue": "🟡",
                    "significant_issue": "🟠",
                    "critical_issue": "🔴",
                }
                severity_icon = severity_colors.get(severity, "⚪")

                col_score, col_sev = st.columns([1, 3])
                with col_score:
                    st.metric("Trade Quality Score", f"{score}/10")
                with col_sev:
                    st.markdown(
                        f"**{severity_icon} Severity:** "
                        f"{severity.replace('_', ' ').title()}"
                    )

                st.divider()

                # ── Analysis sections ──────────────────────────────────────────
                ac1, ac2 = st.columns(2)

                with ac1:
                    st.markdown("**🎯 Psychological Pattern**")
                    st.info(analysis.get("psychological_pattern", "—"))

                    st.markdown("**✅ What Went Well**")
                    st.success(analysis.get("what_went_well", "—"))

                    st.markdown("**⚠️ Primary Mistake**")
                    mistake = analysis.get("primary_mistake", "None")
                    if mistake and mistake != "None":
                        st.warning(mistake)
                    else:
                        st.success("No significant mistakes identified")

                with ac2:
                    st.markdown("**📊 Risk Management**")
                    st.info(analysis.get("risk_management_assessment", "—"))

                    st.markdown("**🔍 Root Cause**")
                    root = analysis.get("root_cause", "—")
                    st.info(root)

                    st.markdown("**❌ What Went Wrong**")
                    wrong = analysis.get("what_went_wrong", "None")
                    if wrong and wrong != "None":
                        st.error(wrong)
                    else:
                        st.success("No significant issues")

                st.divider()

                # ── Specific suggestions ───────────────────────────────────────
                st.markdown("**💡 Specific Suggestions**")
                suggestions = analysis.get("specific_suggestions", [])
                for i, suggestion in enumerate(suggestions, 1):
                    st.markdown(f"**{i}.** {suggestion}")

                # ── Token usage ────────────────────────────────────────────────
                st.divider()
                st.caption(
                    f"Model: {result['model']} | "
                    f"Tokens used: {result['total_tokens']} | "
                    f"Generated: {result['generated_at'][:19]}"
                )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PATTERN DETECTION
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("#### Behavioral Pattern Detection")
    st.caption(
        "AI analyzes your complete trading history to identify "
        "systematic behavioral biases and their financial impact."
    )

    st.info(
        f"This analysis is based on your {len(df)} closed trades. "
        "More trades = more accurate pattern detection."
    )

    pattern_btn = st.button(
        "🔍 Detect My Behavioral Patterns",
        type="primary",
    )

    if pattern_btn:
        with st.spinner(
            "AI is analyzing your complete trading history... "
            "This takes 10-20 seconds."
        ):
            ai_context = analytics.build_ai_context(df)
            result = ai.detect_behavioral_patterns(ai_context)

        if not result["success"]:
            st.error(f"Pattern detection failed: {result['error']}")
        else:
            patterns = result["patterns"]

            # ── Performance grade ──────────────────────────────────────────────
            grade = patterns.get("performance_grade", "?")
            grade_colors = {
                "A": "🟢", "B": "🟢",
                "C": "🟡", "D": "🟠", "F": "🔴"
            }
            grade_icon = grade_colors.get(grade, "⚪")

            pg1, pg2 = st.columns([1, 4])
            with pg1:
                st.metric("Performance Grade", f"{grade_icon} {grade}")
            with pg2:
                st.markdown(
                    f"**Overall Assessment:** "
                    f"{patterns.get('overall_assessment', '—')}"
                )

            st.divider()

            # ── Critical patterns ──────────────────────────────────────────────
            critical = patterns.get("critical_patterns", [])
            if critical:
                st.markdown("#### 🚨 Critical Behavioral Patterns")
                st.caption(
                    "Ranked by financial impact — most costly first"
                )

                for i, pattern in enumerate(critical, 1):
                    with st.expander(
                        f"**Pattern {i}: {pattern.get('pattern_name', 'Unknown')}**",
                        expanded=(i == 1),
                    ):
                        pc1, pc2 = st.columns(2)
                        with pc1:
                            st.markdown("**📊 Evidence**")
                            st.info(pattern.get("evidence", "—"))
                            st.markdown("**💸 Financial Impact**")
                            st.warning(pattern.get("financial_impact", "—"))
                        with pc2:
                            st.markdown("**✅ Correction**")
                            st.success(pattern.get("correction", "—"))

            st.divider()

            # ── Strengths ──────────────────────────────────────────────────────
            strengths = patterns.get("strengths", [])
            if strengths:
                st.markdown("#### 💪 Your Strengths")
                for strength in strengths:
                    st.success(f"✅ {strength}")

            st.divider()

            # ── Top priority action ────────────────────────────────────────────
            st.markdown("#### 🎯 Top Priority Action")
            top_action = patterns.get("top_priority_action", "—")
            estimated = patterns.get("estimated_improvement", "—")
            st.error(f"**Action:** {top_action}")
            st.info(f"**Estimated improvement:** {estimated}")

            # ── Token usage ────────────────────────────────────────────────────
            st.divider()
            st.caption(
                f"Model: {result['model']} | "
                f"Tokens used: {result['total_tokens']} | "
                f"Analyzed {len(df)} trades"
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WEEKLY REVIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("#### Weekly Performance Review")
    st.caption(
        "AI-generated coaching summary for the past 7 days — "
        "behavioral patterns, highlights, and focus for next week."
    )

    # Get trades from last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    df["entry_date"] = df["entry_date"].apply(
        lambda x: x if hasattr(x, "year") else datetime.fromisoformat(str(x))
    )

    weekly_df = df[df["entry_date"] >= cutoff]
    weekly_trades = repo.get_all_trades(closed_only=True)
    weekly_trades = [
        t for t in weekly_trades
        if datetime.fromisoformat(t["entry_date"]) >= cutoff
    ]

    st.metric("Trades This Week", len(weekly_trades))

    if not weekly_trades:
        st.info(
            "No trades in the past 7 days. "
            "Log some trades to generate a weekly review."
        )
    else:
        weekly_btn = st.button(
            "📅 Generate Weekly Review",
            type="primary",
        )

        if weekly_btn:
            with st.spinner("Generating your weekly review..."):
                ai_context = analytics.build_ai_context(df)
                result = ai.generate_weekly_summary(
                    weekly_trades, ai_context
                )

            if not result["success"]:
                st.error(f"Weekly review failed: {result['error']}")
            else:
                summary = result["summary"]

                # Grade and headline
                grade = summary.get("week_grade", "?")
                grade_icon = {
                    "A": "🟢", "B": "🟢",
                    "C": "🟡", "D": "🟠", "F": "🔴"
                }.get(grade, "⚪")

                wc1, wc2 = st.columns([1, 4])
                with wc1:
                    st.metric("Week Grade", f"{grade_icon} {grade}")
                with wc2:
                    st.markdown(
                        f"**{summary.get('headline', '—')}**"
                    )

                st.divider()

                # Performance narrative
                st.markdown("#### 📖 This Week's Story")
                st.markdown(summary.get("performance_narrative", "—"))

                st.divider()

                wc3, wc4 = st.columns(2)
                with wc3:
                    st.markdown("#### 🏆 Best Moment")
                    st.success(summary.get("best_moment", "—"))

                    st.markdown("#### 😌 Emotional Pattern")
                    st.info(summary.get("emotional_pattern", "—"))

                with wc4:
                    st.markdown("#### 📚 Learning Moment")
                    st.warning(summary.get("learning_moment", "—"))

                    st.markdown("#### 🎯 Focus for Next Week")
                    st.error(summary.get("focus_for_next_week", "—"))

                st.caption(
                    f"Model: {result['model']} | "
                    f"Tokens used: {result['total_tokens']} | "
                    f"Based on {result['trade_count']} trades"
                )
