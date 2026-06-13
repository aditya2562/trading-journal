import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from datetime import datetime, date, time

from core.trade_repository import TradeRepository
from core.market_data import MarketDataService
from app.utils import load_trades_df, load_open_trades, render_sidebar

from app.auth import require_auth, render_user_menu

st.set_page_config(
    page_title="Log Trade — AI Trading Journal",
    page_icon="📝",
    layout="wide",
)

user = require_auth()
if not user:
    st.stop()

render_user_menu(user)
render_sidebar(user_id=user["id"])

st.title("📝 Trade Log")
st.caption("Record your trades with full psychological and market context")
st.divider()

repo = TradeRepository()

# ── Two Tabs ───────────────────────────────────────────────────────────────────
tab_log, tab_close = st.tabs(["📥 Log New Trade", "✅ Close Open Trade"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LOG NEW TRADE
# ══════════════════════════════════════════════════════════════════════════════

with tab_log:
    st.markdown("#### New Trade Entry")
    st.caption(
        "Fill in all fields you know at entry time. "
        "You can close the trade later from the 'Close Open Trade' tab."
    )

    # st.form groups all inputs — only submits when button clicked.
    # Without a form, every keystroke triggers a full rerun.
    is_closed = st.checkbox(
        "✅ This trade is already closed",
        help="Check this before filling the form if logging a completed trade"
    )

    with st.form("new_trade_form", clear_on_submit=True):

        # ── SECTION 1: What Was Traded ─────────────────────────────────────────
        st.markdown("**What Was Traded**")
        col1, col2, col3 = st.columns(3)

        with col1:
            ticker = st.text_input(
                "Ticker Symbol *",
                placeholder="AAPL",
                help="Stock ticker symbol. Will be uppercased automatically."
            ).upper().strip()

        with col2:
            quantity = st.number_input(
                "Quantity (Shares) *",
                min_value=0.01,
                value=10.0,
                step=1.0,
                help="Number of shares traded"
            )

        with col3:
            direction = st.selectbox(
                "Direction",
                options=["long", "short"],
                index=0,
            )

        col4, col5 = st.columns(2)
        with col4:
            company_name = st.text_input(
                "Company Name",
                placeholder="Apple Inc.",
            )
        with col5:
            sector = st.selectbox(
                "Sector",
                options=[
                    "", "Technology", "Healthcare", "Financials",
                    "Energy", "Consumer Discretionary", "Industrials",
                    "Communication Services", "Materials",
                    "Consumer Staples", "Utilities", "Real Estate"
                ],
            )

        st.markdown("---")

        # ── SECTION 2: Entry Details ───────────────────────────────────────────
        st.markdown("**Entry Details**")
        col6, col7, col8 = st.columns(3)

        with col6:
            entry_price = st.number_input(
                "Entry Price *",
                min_value=0.01,
                value=100.00,
                step=0.01,
                format="%.2f",
            )
        with col7:
            entry_date_val = st.date_input(
                "Entry Date *",
                value=date.today(),
            )
        with col8:
            entry_time_val = st.time_input(
                "Entry Time",
                value=time(9, 30),  # Default: market open
            )

        st.markdown("---")

        # ── SECTION 3: Risk Management ─────────────────────────────────────────
        st.markdown("**Risk Management** *(optional but recommended)*")
        col9, col10, col11 = st.columns(3)

        with col9:
            stop_loss = st.number_input(
                "Stop Loss Price",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Price at which you'll exit if wrong"
            )
        with col10:
            take_profit = st.number_input(
                "Take Profit Price",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Price at which you'll exit if right"
            )
        with col11:
            commission = st.number_input(
                "Commission ($)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
            )

        # Live R:R preview — shows calculated R:R as user types
        # This teaches traders to think about R:R before entry
        if stop_loss > 0 and take_profit > 0 and entry_price > 0:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            if risk > 0:
                rr = reward / risk
                color = "🟢" if rr >= 2.0 else "🟡" if rr >= 1.0 else "🔴"
                st.info(
                    f"{color} **Planned R:R: {rr:.2f}:1** — "
                    f"Risk: ${risk:.2f}/share | "
                    f"Reward: ${reward:.2f}/share"
                )

        st.markdown("---")

        # ── SECTION 4: Strategy ────────────────────────────────────────────────
        st.markdown("**Strategy**")
        col12, col13 = st.columns(2)

        with col12:
            strategy_name = st.selectbox(
                "Strategy",
                options=[
                    "", "Breakout", "Momentum", "Mean Reversion",
                    "Earnings Play", "Gap Fill", "Trend Following",
                    "Support/Resistance", "FOMO", "Other"
                ],
            )
        with col13:
            timeframe = st.selectbox(
                "Timeframe",
                options=["", "scalp", "intraday", "swing", "position"],
            )

        setup_description = st.text_area(
            "Setup Description",
            placeholder="What specific pattern or setup triggered this trade?",
            height=80,
        )

        st.markdown("---")

        # ── SECTION 5: Psychology ──────────────────────────────────────────────
        st.markdown("**Psychology** *(most important section)*")
        col14, col15 = st.columns(2)

        with col14:
            emotional_state = st.selectbox(
                "Emotional State at Entry *",
                options=[
                    "calm", "confident", "neutral",
                    "anxious", "fearful", "excited", "revenge"
                ],
                help="Be honest. This is the data that makes AI analysis powerful."
            )
        with col15:
            confidence_level = st.slider(
                "Confidence Level *",
                min_value=1,
                max_value=10,
                value=5,
                help="1 = very uncertain, 10 = extremely confident"
            )

        col16, col17 = st.columns(2)
        with col16:
            fomo_factor = st.checkbox(
                "🚨 FOMO Trade — I chased this move",
                help="Did you enter because you feared missing out, not because of a setup?"
            )
        with col17:
            followed_plan = st.checkbox(
                "✅ Followed a predefined plan",
                value=True,
                help="Did you have a written plan before entering?"
            )

        entry_reasoning = st.text_area(
            "Entry Reasoning *",
            placeholder="Why did you enter this trade? What was your thesis?",
            height=100,
            help="This text is fed directly to the AI for analysis. Be specific."
        )

        pre_trade_notes = st.text_area(
            "Pre-Trade Notes",
            placeholder="Any other observations before entry...",
            height=60,
        )

        st.markdown("---")

        # ── SECTION 6: Market Context ──────────────────────────────────────────
        st.markdown("**Market Context**")
        col18, col19, col20 = st.columns(3)

        with col18:
            market_condition = st.selectbox(
                "Market Condition",
                options=["", "trending up", "trending down", "ranging", "volatile"],
            )
        with col19:
            spy_direction = st.selectbox(
                "SPY Direction (overall market)",
                options=["", "up", "down", "flat"],
            )
        with col20:
            sector_performance = st.number_input(
                "Sector Performance (%)",
                value=0.0,
                step=0.1,
                format="%.2f",
                help="How did the sector perform today? (e.g. +1.2 or -0.8)"
            )

        st.markdown("---")

        # ── SECTION 7: Exit (optional — for already closed trades) ─────────────
        st.markdown("**Exit Details** *(fill if trade is already closed)*")

        exit_price = None
        exit_date_str = None
        exit_reason = None
        exit_reasoning = None
        stop_loss_honored = None

        if is_closed:
            col21, col22, col23 = st.columns(3)
            with col21:
                exit_price = st.number_input(
                    "Exit Price",
                    min_value=0.01,
                    value=100.00,
                    step=0.01,
                    format="%.2f",
                )
            with col22:
                exit_date_val = st.date_input("Exit Date", value=date.today())
            with col23:
                exit_time_val = st.time_input("Exit Time", value=time(15, 30))

            exit_reason = st.selectbox(
                "Exit Reason",
                options=[
                    "take profit hit", "stop loss hit",
                    "manual", "time"
                ],
            )
            exit_reasoning = st.text_area(
                "Exit Reasoning",
                placeholder="Why did you exit?",
                height=80,
            )
            stop_loss_honored = st.radio(
                "Was your stop loss honored? (not moved or ignored)",
                options=[
                    "Yes — I honored my stop loss",
                    "No — I moved or ignored it",
                    "No stop loss was set"
                ],
                index=0 if stop_loss > 0 else 2,
                help="This tells the AI whether you followed your risk plan"
            )

            exit_date_str = datetime.combine(
                exit_date_val, exit_time_val
            ).isoformat()

        # ── Submit ─────────────────────────────────────────────────────────────
        submitted = st.form_submit_button(
            "📥 Log Trade",
            use_container_width=True,
            type="primary",
        )

    # ── Form Submission Handler ────────────────────────────────────────────────
    # This runs OUTSIDE the form block but only when submitted=True
    if submitted:
        # Validate required fields
        if not ticker:
            st.error("Ticker symbol is required.")
        elif entry_price <= 0:
            st.error("Entry price must be greater than zero.")
        elif not entry_reasoning:
            st.error("Entry reasoning is required — the AI needs this.")
        else:
            # Build trade data dictionary
            entry_date_str = datetime.combine(
                entry_date_val, entry_time_val
            ).isoformat()

            trade_data = {
                "ticker": ticker,
                "company_name": company_name or None,
                "sector": sector or None,
                "quantity": quantity,
                "direction": direction,
                "entry_price": entry_price,
                "entry_date": entry_date_str,
                "commission": commission,
                "strategy_name": strategy_name or None,
                "timeframe": timeframe or None,
                "setup_description": setup_description or None,
                "emotional_state": emotional_state,
                "confidence_level": confidence_level,
                "fomo_factor": int(fomo_factor),
                "followed_plan": int(followed_plan),
                "entry_reasoning": entry_reasoning,
                "pre_trade_notes": pre_trade_notes or None,
                "market_condition": market_condition or None,
                "spy_direction": spy_direction or None,
                "sector_performance": sector_performance if sector_performance != 0.0 else None,
            }

            # Add risk management if provided
            if stop_loss > 0:
                trade_data["stop_loss_price"] = stop_loss
            if take_profit > 0:
                trade_data["take_profit_price"] = take_profit

            # Add exit data if trade is closed
            if is_closed and exit_price:
                trade_data["exit_price"] = exit_price
                trade_data["exit_date"] = exit_date_str
                trade_data["exit_reason"] = exit_reason
                trade_data["exit_reasoning"] = exit_reasoning or None
                if "No stop loss" not in stop_loss_honored:
                    trade_data["stop_loss_honored"] = (
                        1 if "Yes" in stop_loss_honored else 0
                    )

            try:
                trade_id = repo.insert_trade(trade_data, user_id=user["id"])
                # Clear cache so dashboard reflects new trade immediately
                st.cache_data.clear()
                st.success(
                    f"✅ Trade #{trade_id} logged successfully! "
                    f"{ticker} @ ${entry_price:.2f}"
                )
            except Exception as e:
                st.error(f"Failed to log trade: {e}")
    
# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CLOSE OPEN TRADE
# ══════════════════════════════════════════════════════════════════════════════

with tab_close:
    st.markdown("#### Close an Open Trade")

    open_trades = load_open_trades(user_id=user["id"])

    if not open_trades:
        st.info("No open trades to close. Log a trade first.")
    else:
        # Build human-readable labels for the selectbox
        # Each option shows: "AAPL — 10 shares @ $185.50 (opened Jan 15)"
        trade_labels = []
        for t in open_trades:
            entry_dt = datetime.fromisoformat(t["entry_date"])
            label = (
                f"{t['ticker']} — {t['quantity']} shares "
                f"@ ${t['entry_price']:.2f} "
                f"(opened {entry_dt.strftime('%b %d, %Y')})"
            )
            trade_labels.append(label)

        selected_label = st.selectbox(
            "Select Trade to Close",
            options=trade_labels,
        )

        # Get the actual trade dict that matches selected label
        selected_idx = trade_labels.index(selected_label)
        selected_trade = open_trades[selected_idx]

        # Show the selected trade details
        with st.expander("📋 Trade Details", expanded=True):
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                st.metric("Ticker", selected_trade["ticker"])
                st.metric("Strategy", selected_trade.get("strategy_name") or "—")
            with dc2:
                st.metric("Entry Price", f"${selected_trade['entry_price']:.2f}")
                st.metric("Quantity", selected_trade["quantity"])
            with dc3:
                st.metric(
                    "Stop Loss",
                    f"${selected_trade['stop_loss_price']:.2f}"
                    if selected_trade.get("stop_loss_price") else "—"
                )
                st.metric(
                    "Take Profit",
                    f"${selected_trade['take_profit_price']:.2f}"
                    if selected_trade.get("take_profit_price") else "—"
                )

        st.markdown("---")

        with st.form("close_trade_form", clear_on_submit=True):
            st.markdown("**Exit Details**")

            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                close_exit_price = st.number_input(
                    "Exit Price *",
                    min_value=0.01,
                    value=float(selected_trade["entry_price"]),
                    step=0.01,
                    format="%.2f",
                )
            with cc2:
                close_exit_date = st.date_input(
                    "Exit Date *",
                    value=date.today(),
                )
            with cc3:
                close_exit_time = st.time_input(
                    "Exit Time",
                    value=time(15, 30),
                )

            close_exit_reason = st.selectbox(
                "Exit Reason *",
                options=[
                    "take profit hit", "stop loss hit",
                    "manual", "time"
                ],
            )

            close_exit_reasoning = st.text_area(
                "Exit Reasoning",
                placeholder="Why did you exit? What happened?",
                height=100,
            )

            close_stop_honored = None
            if selected_trade.get("stop_loss_price"):
                close_stop_honored = st.radio(
                    "Was your stop loss honored? (not moved or ignored)",
                    options=["Yes — I honored my stop loss", "No — I moved or ignored it"],
                    index=0,
                )

            # Live P&L preview
            if close_exit_price > 0:
                preview_pnl = (
                    close_exit_price - selected_trade["entry_price"]
                ) * selected_trade["quantity"]
                preview_color = "🟢" if preview_pnl >= 0 else "🔴"
                st.info(
                    f"{preview_color} **Projected P&L: "
                    f"${preview_pnl:+,.2f}**"
                )

            close_submitted = st.form_submit_button(
                "✅ Close Trade",
                use_container_width=True,
                type="primary",
            )

        if close_submitted:
            exit_dt_str = datetime.combine(
                close_exit_date, close_exit_time
            ).isoformat()

            final_stop_honored = None
            if selected_trade.get("stop_loss_price") and close_stop_honored:
                final_stop_honored = True if "Yes" in close_stop_honored else False

            success = repo.close_trade(
                trade_id=selected_trade["id"],
                exit_price=close_exit_price,
                exit_date=exit_dt_str,
                exit_reason=close_exit_reason,
                exit_reasoning=close_exit_reasoning or None,
                stop_loss_honored=final_stop_honored,
                user_id=user["id"],
            )

            if success:
                st.cache_data.clear()
                final_pnl = (
                    close_exit_price - selected_trade["entry_price"]
                ) * selected_trade["quantity"]
                outcome = "WIN 🟢" if final_pnl > 0 else "LOSS 🔴"
                st.success(
                    f"Trade closed — {outcome} | "
                    f"P&L: ${final_pnl:+,.2f}"
                )
            else:
                st.error("Failed to close trade.")