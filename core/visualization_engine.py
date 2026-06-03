import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

COLORS = {
    # Semantic colors — meaning-driven
    "win":          "#26a69a",    # Teal green — profit, positive
    "loss":         "#ef5350",    # Red — loss, negative
    "breakeven":    "#ffa726",    # Orange — neutral outcome
    "open":         "#42a5f5",    # Blue — open position

    # Brand colors — UI consistency
    "primary":      "#2196F3",    # Primary blue — main actions
    "secondary":    "#7c4dff",    # Purple — secondary emphasis
    "accent":       "#00bcd4",    # Cyan — highlights

    # Emotional state colors
    "calm":         "#26a69a",    # Teal — controlled
    "confident":    "#42a5f5",    # Blue — assured
    "anxious":      "#ef5350",    # Red — stressed
    "fearful":      "#ff7043",    # Deep orange — fear
    "excited":      "#ffa726",    # Orange — overexcited
    "revenge":      "#ab47bc",    # Purple — dangerous state
    "neutral":      "#78909c",    # Blue grey — baseline

    # Background and surface
    "background":   "#0e1117",    # Dark background (Streamlit default)
    "surface":      "#1a1d23",    # Slightly lighter surface
    "surface2":     "#23272f",    # Card/panel background
    "border":       "#2d3139",    # Subtle borders

    # Text
    "text_primary": "#fafafa",    # Primary text
    "text_secondary": "#9ea3ad",  # Secondary/muted text

    # Grid
    "grid":         "#2d3139",    # Chart grid lines
}

# Standard figure dimensions
CHART_HEIGHT = {
    "small":   300,
    "medium":  420,
    "large":   520,
    "xlarge":  650,
}

class VisualizationEngine:

    def _apply_theme(
        self,
        fig: go.Figure,
        title: str = "",
        xaxis_title: str = "",
        yaxis_title: str = "",
        height: int = CHART_HEIGHT["medium"],
        show_legend: bool = False,
    ) -> go.Figure:

        fig.update_layout(
            title=dict(
                text=title,
                font=dict(
                    color=COLORS["text_primary"],
                    size=15,
                    family="Inter, -apple-system, sans-serif"
                ),
                x=0.0,           # Left-align titles
                xanchor="left",
            ),

            # Background colors
            plot_bgcolor=COLORS["surface"],
            paper_bgcolor=COLORS["background"],

            # Font defaults
            font=dict(
                color=COLORS["text_secondary"],
                size=12,
                family="Inter, -apple-system, sans-serif"
            ),

            # X-axis styling
            xaxis=dict(
                title=dict(
                    text=xaxis_title,
                    font=dict(color=COLORS["text_secondary"], size=11)
                ),
                gridcolor=COLORS["grid"],
                gridwidth=1,
                showgrid=True,
                zeroline=False,
                tickfont=dict(color=COLORS["text_secondary"], size=11),
                linecolor=COLORS["border"],
                showline=True,
            ),

            # Y-axis styling
            yaxis=dict(
                title=dict(
                    text=yaxis_title,
                    font=dict(color=COLORS["text_secondary"], size=11)
                ),
                gridcolor=COLORS["grid"],
                gridwidth=1,
                showgrid=True,
                zeroline=False,
                tickfont=dict(color=COLORS["text_secondary"], size=11),
                linecolor=COLORS["border"],
                showline=False,
            ),

            # Legend
            showlegend=show_legend,
            legend=dict(
                bgcolor=COLORS["surface2"],
                bordercolor=COLORS["border"],
                borderwidth=1,
                font=dict(color=COLORS["text_secondary"], size=11),
            ),

            # Margins — enough breathing room, not wasteful
            margin=dict(l=40, r=20, t=50, b=40),

            # Chart dimensions
            height=height,

            # Hover styling
            hoverlabel=dict(
                bgcolor=COLORS["surface2"],
                bordercolor=COLORS["border"],
                font=dict(color=COLORS["text_primary"], size=12),
            ),
        )

        return fig

    def _empty_chart(self, message: str = "No Data Availabel") -> go.Figure:

        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(
                color=COLORS["text_secondary"],
                size=14,
            )
        )
        return self._apply_theme(fig, height=CHART_HEIGHT["medium"])

    def pnl_curve(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("Log trades to see your P&L curve")

        from core.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine()
        curve = engine.compute_pnl_curve(df)

        if curve.empty:
            return self._empty_chart("No closed trades yet")

        fig = go.Figure()

        # ── Main P&L line ──────────────────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=curve["entry_date"],
            y=curve["cumulative_pnl"],

            # mode="lines" = connected line, no dots at each point
            mode="lines",
            name="Cumulative P&L",

            # Line color: green if ending positive, red if negative
            line=dict(
                color=COLORS["win"] if curve["cumulative_pnl"].iloc[-1] >= 0
                else COLORS["loss"],
                width=2.5,
            ),

            # Fill to zero — shades the area under the curve
            # This makes gains (above zero) visually distinct from losses
            fill="tozeroy",
            fillcolor=(
                "rgba(38, 166, 154, 0.12)"    # Transparent teal for gains
                if curve["cumulative_pnl"].iloc[-1] >= 0
                else "rgba(239, 83, 80, 0.12)"  # Transparent red for losses
            ),

            # Hover template — what shows when user hovers over the line
            hovertemplate=(
                "<b>Date:</b> %{x|%b %d, %Y}<br>"
                "<b>Cumulative P&L:</b> $%{y:,.2f}"
                "<extra></extra>"    # Removes the trace name box
            ),
        ))

        # ── Zero line (breakeven reference) ───────────────────────────────────
        # A horizontal line at y=0 separates profit from loss territory
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color=COLORS["text_secondary"],
            line_width=1,
            opacity=0.5,
        )

        # ── Annotate final value ───────────────────────────────────────────────
        final_pnl = curve["cumulative_pnl"].iloc[-1]
        fig.add_annotation(
            x=curve["entry_date"].iloc[-1],
            y=final_pnl,
            text=f"  ${final_pnl:+,.2f}",
            showarrow=False,
            font=dict(
                color=COLORS["win"] if final_pnl >= 0 else COLORS["loss"],
                size=13,
                family="Inter, sans-serif",
            ),
            xanchor="left",
        )

        return self._apply_theme(
            fig,
            title="Cumulative P&L",
            xaxis_title="Date",
            yaxis_title="P&L ($)",
            height=CHART_HEIGHT["large"],
        )

    def pnl_distribution(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No trade data for distribution")

        fig = go.Figure()

        wins = df[df["outcome"] == "win"]["net_pnl"]
        losses = df[df["outcome"] == "loss"]["net_pnl"]

        # ── Loss distribution ─────────────────────────────────────────────────
        if len(losses) > 0:
            fig.add_trace(go.Histogram(
                x=losses,
                name="Losses",
                marker_color=COLORS["loss"],
                opacity=0.75,
                nbinsx=20,
                hovertemplate=(
                    "<b>P&L Range:</b> $%{x}<br>"
                    "<b>Count:</b> %{y} trades"
                    "<extra></extra>"
                ),
            ))

        # ── Win distribution ──────────────────────────────────────────────────
        if len(wins) > 0:
            fig.add_trace(go.Histogram(
                x=wins,
                name="Wins",
                marker_color=COLORS["win"],
                opacity=0.75,
                nbinsx=20,
                hovertemplate=(
                    "<b>P&L Range:</b> $%{x}<br>"
                    "<b>Count:</b> %{y} trades"
                    "<extra></extra>"
                ),
            ))

        # barmode="overlay" overlaps the two histograms
        # Alternative: "stack" stacks them, "group" places side by side
        fig.update_layout(barmode="overlay")

        # Zero line
        fig.add_vline(
            x=0,
            line_dash="dash",
            line_color=COLORS["text_secondary"],
            line_width=1.5,
            opacity=0.7,
        )

        return self._apply_theme(
            fig,
            title="P&L Distribution",
            xaxis_title="Trade P&L ($)",
            yaxis_title="Number of Trades",
            height=CHART_HEIGHT["medium"],
            show_legend=True,
        )

    def monthly_pnl_bar(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No data for monthly P&L")

        from core.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine()
        monthly = engine.compute_pnl_by_period(df, period="ME")

        if monthly.empty:
            return self._empty_chart("Insufficient data for monthly view")

        # Format period labels as "Jan 2025"
        monthly["period_label"] = pd.to_datetime(
            monthly["period"]
        ).dt.strftime("%b %Y")

        # Color each bar by whether that month was profitable
        bar_colors = [
            COLORS["win"] if pnl >= 0 else COLORS["loss"]
            for pnl in monthly["net_pnl"]
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=monthly["period_label"],
            y=monthly["net_pnl"],
            marker_color=bar_colors,
            text=[f"${v:+,.0f}" for v in monthly["net_pnl"]],
            textposition="outside",
            textfont=dict(color=COLORS["text_secondary"], size=10),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "P&L: $%{y:,.2f}<br>"
                "<extra></extra>"
            ),
        ))

        fig.add_hline(y=0, line_color=COLORS["border"], line_width=1)

        return self._apply_theme(
            fig,
            title="Monthly P&L",
            xaxis_title="Month",
            yaxis_title="Net P&L ($)",
            height=CHART_HEIGHT["medium"],
        )

    def win_loss_donut(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No trades to display")

        outcome_counts = df["outcome"].value_counts()

        labels = []
        values = []
        colors = []

        outcome_color_map = {
            "win": COLORS["win"],
            "loss": COLORS["loss"],
            "breakeven": COLORS["breakeven"],
            "open": COLORS["open"],
        }

        for outcome, count in outcome_counts.items():
            labels.append(outcome.capitalize())
            values.append(count)
            colors.append(outcome_color_map.get(outcome, COLORS["primary"]))

        total = sum(values)
        win_count = outcome_counts.get("win", 0)
        win_rate = (win_count / total * 100) if total > 0 else 0

        fig = go.Figure()

        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            hole=0.65,          # The hole makes it a donut
            marker=dict(
                colors=colors,
                line=dict(color=COLORS["background"], width=3)
            ),
            textinfo="label+percent",
            textfont=dict(color=COLORS["text_primary"], size=12),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Count: %{value}<br>"
                "Share: %{percent}"
                "<extra></extra>"
            ),
        ))

        # Center annotation — win rate displayed inside the donut hole
        fig.add_annotation(
            text=f"<b>{win_rate:.1f}%</b><br><span style='font-size:11px'>Win Rate</span>",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(
                color=COLORS["text_primary"],
                size=18,
            ),
            align="center",
        )

        return self._apply_theme(
            fig,
            title="Trade Outcomes",
            height=CHART_HEIGHT["medium"],
            show_legend=True,
        )

    def performance_by_category(self, data: pd.DataFrame, category_col: str, title: str, question: str = "",) -> go.Figure:

        if data is None or data.empty:
            return self._empty_chart(f"No data for {title}")

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Win Rate (%)", "Avg P&L ($)"),
            # horizontal_spacing controls gap between subplots
            horizontal_spacing=0.12,
        )

        categories = data[category_col].tolist()

        # ── Left: Win Rate bars ────────────────────────────────────────────────
        win_rate_colors = [
            COLORS["win"] if wr >= 50 else COLORS["loss"]
            for wr in data["win_rate"]
        ]

        fig.add_trace(
            go.Bar(
                x=categories,
                y=data["win_rate"],
                marker_color=win_rate_colors,
                text=[f"{v:.1f}%" for v in data["win_rate"]],
                textposition="outside",
                textfont=dict(color=COLORS["text_secondary"], size=10),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Win Rate: %{y:.1f}%<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1, col=1
        )

        # 50% reference line — breakeven win rate
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color=COLORS["text_secondary"],
            line_width=1,
            opacity=0.5,
            row=1, col=1,
        )

        # ── Right: Average P&L bars ────────────────────────────────────────────
        avg_pnl_colors = [
            COLORS["win"] if pnl >= 0 else COLORS["loss"]
            for pnl in data["avg_pnl"]
        ]

        fig.add_trace(
            go.Bar(
                x=categories,
                y=data["avg_pnl"],
                marker_color=avg_pnl_colors,
                text=[f"${v:+.0f}" for v in data["avg_pnl"]],
                textposition="outside",
                textfont=dict(color=COLORS["text_secondary"], size=10),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Avg P&L: $%{y:+.2f}<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1, col=2
        )

        fig.add_hline(
            y=0,
            line_color=COLORS["border"],
            line_width=1,
            row=1, col=2,
        )

        # Apply theme to subplots manually
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(color=COLORS["text_primary"], size=15),
                x=0.0,
            ),
            plot_bgcolor=COLORS["surface"],
            paper_bgcolor=COLORS["background"],
            font=dict(color=COLORS["text_secondary"], size=11),
            height=CHART_HEIGHT["medium"],
            margin=dict(l=40, r=20, t=70, b=40),
            hoverlabel=dict(
                bgcolor=COLORS["surface2"],
                bordercolor=COLORS["border"],
                font=dict(color=COLORS["text_primary"], size=12),
            ),
        )

        # Style all axes consistently
        fig.update_xaxes(
            gridcolor=COLORS["grid"],
            tickfont=dict(color=COLORS["text_secondary"]),
            linecolor=COLORS["border"],
        )
        fig.update_yaxes(
            gridcolor=COLORS["grid"],
            tickfont=dict(color=COLORS["text_secondary"]),
            zeroline=False,
        )

        # Style subplot title fonts
        for annotation in fig.layout.annotations:
            annotation.font.color = COLORS["text_secondary"]
            annotation.font.size = 12

        return fig

    def drawdown_chart(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No data for drawdown analysis")

        from core.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine()
        dd_data = engine.compute_drawdown(df)

        dd_curve = dd_data.get("drawdown_curve", pd.DataFrame())

        if dd_curve.empty:
            return self._empty_chart("Insufficient data for drawdown")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dd_curve["entry_date"],
            y=dd_curve["drawdown_pct"],
            mode="lines",
            name="Drawdown",
            line=dict(color=COLORS["loss"], width=2),
            fill="tozeroy",
            fillcolor="rgba(239, 83, 80, 0.15)",
            hovertemplate=(
                "<b>Date:</b> %{x|%b %d, %Y}<br>"
                "<b>Drawdown:</b> %{y:.2f}%"
                "<extra></extra>"
            ),
        ))

        # Max drawdown annotation
        max_dd = dd_data["max_drawdown_pct"]
        max_dd_idx = dd_curve["drawdown_pct"].idxmin()

        if pd.notna(max_dd_idx):
            fig.add_annotation(
                x=dd_curve.loc[max_dd_idx, "entry_date"],
                y=dd_curve.loc[max_dd_idx, "drawdown_pct"],
                text=f"Max: {max_dd:.1f}%",
                showarrow=True,
                arrowhead=2,
                arrowcolor=COLORS["loss"],
                font=dict(color=COLORS["loss"], size=11),
                ay=-30,
            )

        # Zero reference line
        fig.add_hline(y=0, line_color=COLORS["border"], line_width=1)

        return self._apply_theme(
            fig,
            title="Drawdown Over Time",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            height=CHART_HEIGHT["medium"],
        )

    def rr_scatter(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No R:R data available")

        rr_df = df.dropna(
            subset=["planned_risk_per_share", "actual_rr_ratio"]
        ).copy()

        if len(rr_df) < 3:
            return self._empty_chart("Need more trades with R:R data")

        rr_df["planned_rr"] = (
            rr_df["planned_reward_per_share"] /
            rr_df["planned_risk_per_share"].replace(0, np.nan)
        )

        rr_df = rr_df.dropna(subset=["planned_rr"])

        if rr_df.empty:
            return self._empty_chart("Insufficient R:R plan data")

        point_colors = rr_df["outcome"].map({
            "win": COLORS["win"],
            "loss": COLORS["loss"],
            "breakeven": COLORS["breakeven"],
        }).fillna(COLORS["primary"])

        fig = go.Figure()

        # ── Scatter points ─────────────────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=rr_df["planned_rr"],
            y=rr_df["actual_rr_ratio"],
            mode="markers",
            marker=dict(
                color=point_colors,
                size=9,
                opacity=0.8,
                line=dict(color=COLORS["background"], width=1),
            ),
            text=rr_df["ticker"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Planned R:R: %{x:.2f}<br>"
                "Actual R:R: %{y:.2f}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

        # ── Perfect execution line (diagonal) ─────────────────────────────────
        # If every trade was executed perfectly, all points would sit exactly on this diagonal line (planned = actual)
        max_val = max(
            rr_df["planned_rr"].max(),
            rr_df["actual_rr_ratio"].max()
        ) * 1.1

        fig.add_trace(go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            name="Perfect Execution",
            line=dict(
                color=COLORS["text_secondary"],
                dash="dash",
                width=1.5,
            ),
        ))

        return self._apply_theme(
            fig,
            title="Planned vs Actual R:R Ratio",
            xaxis_title="Planned R:R",
            yaxis_title="Actual R:R",
            height=CHART_HEIGHT["medium"],
            show_legend=True,
        )

    def rolling_win_rate_chart(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No data for rolling win rate")

        from core.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine()
        rolling = engine.compute_rolling_win_rate(df, window=10)

        if rolling.empty:
            return self._empty_chart("Need more trades for rolling analysis")

        fig = go.Figure()

        # ── Rolling win rate line ──────────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=rolling["trade_number"],
            y=rolling["rolling_win_rate"],
            mode="lines",
            name="Rolling Win Rate (10)",
            line=dict(color=COLORS["primary"], width=2.5),
            fill="tozeroy",
            fillcolor="rgba(33, 150, 243, 0.08)",
            hovertemplate=(
                "<b>Trade #%{x}</b><br>"
                "Rolling Win Rate: %{y:.1f}%"
                "<extra></extra>"
            ),
        ))

        # ── 50% breakeven reference ────────────────────────────────────────────
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color=COLORS["text_secondary"],
            line_width=1.5,
            opacity=0.6,
            annotation_text="50% breakeven",
            annotation_position="bottom right",
            annotation_font_color=COLORS["text_secondary"],
        )

        return self._apply_theme(
            fig,
            title="Rolling Win Rate (Last 10 Trades)",
            xaxis_title="Trade Number",
            yaxis_title="Win Rate (%)",
            height=CHART_HEIGHT["medium"],
        )

    def emotion_performance_chart(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No psychology data available")

        from core.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine()
        emotion_data = engine.win_rate_by_emotional_state(df)

        if emotion_data.empty:
            return self._empty_chart("No emotional state data logged")

        emotion_color_map = {
            "calm":      COLORS["calm"],
            "confident": COLORS["confident"],
            "neutral":   COLORS["neutral"],
            "anxious":   COLORS["anxious"],
            "fearful":   COLORS["fearful"],
            "excited":   COLORS["excited"],
            "revenge":   COLORS["revenge"],
        }

        bar_colors = [
            emotion_color_map.get(e, COLORS["primary"])
            for e in emotion_data["emotional_state"]
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=emotion_data["emotional_state"],
            y=emotion_data["win_rate"],
            marker_color=bar_colors,
            marker_line=dict(color=COLORS["background"], width=1.5),
            text=[
                f"{wr:.1f}%<br><sub>({n} trades)</sub>"
                for wr, n in zip(
                    emotion_data["win_rate"],
                    emotion_data["total_trades"]
                )
            ],
            textposition="outside",
            textfont=dict(color=COLORS["text_secondary"], size=10),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Win Rate: %{y:.1f}%<br>"
                "<extra></extra>"
            ),
        ))

        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color=COLORS["text_secondary"],
            line_width=1.5,
            opacity=0.5,
        )

        return self._apply_theme(
            fig,
            title="Win Rate by Emotional State",
            xaxis_title="Emotional State",
            yaxis_title="Win Rate (%)",
            height=CHART_HEIGHT["medium"],
        )

    def fomo_impact_chart(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No FOMO data available")

        from core.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine()
        psych = engine.compute_psychology_metrics(df)
        fomo = psych["fomo_impact"]

        if fomo["fomo_trade_count"] == 0 and fomo["non_fomo_trade_count"] == 0:
            return self._empty_chart("No FOMO data logged")

        categories = ["FOMO Trades", "Planned Trades"]
        win_rates = [fomo["fomo_win_rate"], fomo["non_fomo_win_rate"]]
        avg_pnls = [fomo["fomo_avg_pnl"], fomo["non_fomo_avg_pnl"]]
        counts = [fomo["fomo_trade_count"], fomo["non_fomo_trade_count"]]

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Win Rate (%)", "Avg P&L ($)"),
            horizontal_spacing=0.15,
        )

        colors = [COLORS["loss"], COLORS["win"]]

        fig.add_trace(
            go.Bar(
                x=categories,
                y=win_rates,
                marker_color=colors,
                text=[
                    f"{wr:.1f}%\n({n} trades)"
                    for wr, n in zip(win_rates, counts)
                ],
                textposition="outside",
                textfont=dict(color=COLORS["text_secondary"], size=11),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Win Rate: %{y:.1f}%"
                    "<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1, col=1,
        )

        pnl_colors = [
            COLORS["loss"] if p < 0 else COLORS["win"]
            for p in avg_pnls
        ]

        fig.add_trace(
            go.Bar(
                x=categories,
                y=avg_pnls,
                marker_color=pnl_colors,
                text=[f"${v:+.2f}" for v in avg_pnls],
                textposition="outside",
                textfont=dict(color=COLORS["text_secondary"], size=11),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Avg P&L: $%{y:+.2f}"
                    "<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1, col=2,
        )

        fig.update_layout(
            title=dict(
                text="FOMO vs Planned Trade Performance",
                font=dict(color=COLORS["text_primary"], size=15),
                x=0.0,
            ),
            plot_bgcolor=COLORS["surface"],
            paper_bgcolor=COLORS["background"],
            font=dict(color=COLORS["text_secondary"], size=11),
            height=CHART_HEIGHT["medium"],
            margin=dict(l=40, r=20, t=70, b=40),
            hoverlabel=dict(
                bgcolor=COLORS["surface2"],
                bordercolor=COLORS["border"],
                font=dict(color=COLORS["text_primary"], size=12),
            ),
        )

        fig.update_xaxes(
            gridcolor=COLORS["grid"],
            tickfont=dict(color=COLORS["text_secondary"]),
        )
        fig.update_yaxes(
            gridcolor=COLORS["grid"],
            tickfont=dict(color=COLORS["text_secondary"]),
            zeroline=False,
        )

        for annotation in fig.layout.annotations:
            annotation.font.color = COLORS["text_secondary"]
            annotation.font.size = 12

        return fig

    def confidence_vs_outcome(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No confidence data")

        conf_df = df.dropna(subset=["confidence_level"]).copy()

        if conf_df.empty:
            return self._empty_chart("No confidence levels logged")

        wins = conf_df[conf_df["outcome"] == "win"]["confidence_level"]
        losses = conf_df[conf_df["outcome"] == "loss"]["confidence_level"]

        fig = go.Figure()

        if len(losses) > 0:
            fig.add_trace(go.Histogram(
                x=losses,
                name="Losses",
                marker_color=COLORS["loss"],
                opacity=0.75,
                xbins=dict(start=1, end=10, size=1),
                hovertemplate=(
                    "<b>Confidence: %{x}</b><br>"
                    "Losses: %{y}"
                    "<extra></extra>"
                ),
            ))

        if len(wins) > 0:
            fig.add_trace(go.Histogram(
                x=wins,
                name="Wins",
                marker_color=COLORS["win"],
                opacity=0.75,
                xbins=dict(start=1, end=10, size=1),
                hovertemplate=(
                    "<b>Confidence: %{x}</b><br>"
                    "Wins: %{y}"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(
            barmode="group",
            xaxis=dict(
                tickmode="linear",
                tick0=1,
                dtick=1,
                title="Confidence Level (1-10)",
            ),
        )

        return self._apply_theme(
            fig,
            title="Confidence Level vs Outcome",
            xaxis_title="Confidence Level (1-10)",
            yaxis_title="Number of Trades",
            height=CHART_HEIGHT["medium"],
            show_legend=True,
        )

    def correlation_bar(self, df: pd.DataFrame) -> go.Figure:

        if df is None or df.empty:
            return self._empty_chart("No correlation data")

        from core.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine()
        corr_df = engine.compute_feature_correlations(df)

        if corr_df.empty:
            return self._empty_chart("Need more trades for correlation (5+ required)")

        # Show top 12 most correlated features
        display = corr_df.head(12).copy()

        # Clean up feature names for display
        display["feature_label"] = display["feature"].str.replace(
            "_", " "
        ).str.title()

        bar_colors = [
            COLORS["win"] if c > 0 else COLORS["loss"]
            for c in display["correlation"]
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            # Horizontal bars — category labels on Y axis
            x=display["correlation"],
            y=display["feature_label"],
            orientation="h",
            marker_color=bar_colors,
            marker_line=dict(color=COLORS["background"], width=1),
            text=[f"{v:+.3f}" for v in display["correlation"]],
            textposition="outside",
            textfont=dict(color=COLORS["text_secondary"], size=10),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Correlation: %{x:+.4f}<br>"
                "<extra></extra>"
            ),
        ))

        # Zero reference line
        fig.add_vline(
            x=0,
            line_color=COLORS["border"],
            line_width=1.5,
        )

        return self._apply_theme(
            fig,
            title="Feature Correlations with Trade Return %",
            xaxis_title="Pearson Correlation",
            yaxis_title="",
            height=CHART_HEIGHT["large"],
        )