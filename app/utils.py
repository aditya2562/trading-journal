import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from core.trade_repository import TradeRepository
from core.analytics_engine import AnalyticsEngine

@st.cache_data(ttl=60)
def load_trades_df() -> pd.DataFrame:

    repo = TradeRepository()
    return repo.get_trades_as_dataframe()

@st.cache_data(ttl=60)
def load_open_trades() -> list:

    repo = TradeRepository()
    return repo.get_open_trades()

def render_sidebar() -> None:

    with st.sidebar:
        st.markdown("---")
        st.markdown("#### 📊 Quick Stats")

        df = load_trades_df()
        open_trades = load_open_trades()

        if df.empty:
            st.caption("No closed trades yet")
        else:
            engine = AnalyticsEngine()
            metrics = engine.compute_summary_metrics(df)

            total_pnl = metrics["total_pnl"]
            st.metric(
                "Total P&L",
                f"${total_pnl:+,.2f}",
            )
            st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
            st.metric("Trades", metrics["total_trades"])
            st.metric(
                "Expectancy",
                f"${metrics['expectancy']:+,.2f}",
                help="Average expected P&L per trade"
            )

        if open_trades:
            st.markdown("---")
            st.markdown(f"#### 🔄 Open: {len(open_trades)}")
            for trade in open_trades[:5]:
                st.caption(
                    f"• {trade['ticker']} "
                    f"@ ${trade['entry_price']}"
                )

        st.markdown("---")
        st.caption("AI Trading Journal v1.0")
