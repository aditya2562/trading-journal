import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AnalyticsEngine:

    def _is_empty(self, df: pd.DataFrame) -> bool:
        return df is None or df.empty

    def compute_summary_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:

        if self._is_empty(df):
            return  {
                "total_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "avg_trade_pnl": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "profit_factor": 0.0,
                "avg_holding_days": 0.0,
                "total_commissions": 0.0,
                "expectancy": 0.0,
            }
        
        total_trades = len(df)

        total_pnl = df["net_pnl"].sum()

        wins = df[df["outcome"] == "win"]
        losses = df[df["outcome"] == "loss"]

        win_rate = (len(wins)/total_trades * 100)if total_trades > 0 else 0.0

        avg_trade_pnl = df["net_pnl"].mean()

        best_trade = df["net_pnl"].max()
        worst_trade = df["net_pnl"].min()

        gross_profit = wins["net_pnl"].sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses["net_pnl"].sum()) if len(losses) > 0 else 0.0

        profit_factor = (gross_profit / gross_loss if gross_loss > 0 else float("inf"))

        df_with_dates = df.dropna(subset=["entry_date", "exit_date"]).copy()
        if not df_with_dates.empty:
            df_with_dates["holding_days"] = (
                pd.to_datetime(df_with_dates["exit_date"]) - pd.to_datetime(df_with_dates["entry_date"])
            ).dt.days

            avg_holding_days = df_with_dates["holding_days"].mean()
        else:
            avg_holding_days = 0.0

        total_commissions = df["comission"].sum()

        avg_win = wins["net_pnl"].mean() if len(wins) > 0 else 0.0
        avg_loss = abs(losses["net_pnl"].mean()) if len(losses) > 0 else 0.0
        loss_rate = 1 - (win_rate / 100)

        expectancy = (win_rate / 100 * avg_win) - (loss_rate * avg_loss)

        return {
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate ,2),
            "avg_trade_pnl": round(avg_trade_pnl, 2),
            "best_trade":round(best_trade, 2),
            "worst_trade":round(worst_trade, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_holding_days":round(avg_holding_days, 1),
            "total_commissions":round(total_commissions, 2),
            "expectancy":round(expectancy, 2),
        }

    def compute_pnl_curve(self, df: pd.DataFrame) -> pd.DataFrame:

        if self._is_empty(df):
            return pd.DataFrame(
                columns=["entry_date", "net_pnl", "cumulative_pnl"]
            )

        curve = df[["entry_date", "net_pnl"]].copy()
        curve = curve.sort_values("entry_date").reset_index(drop=True)

        curve["cumulative_pnl"] = curve["net_pnl"].cumsum()

        return curve

    def compute_pnl_by_period(self, df: pd.DataFrame, period: str = "W") -> pd.DataFrame:

        if self._is_empty(df):
            return pd.DataFrame(columns=["period", "net_pnl", "trade_count"])

        temp = df[["entry_date", "net_pnl"]].copy()
        temp["entry_date"] = pd.to_datetime(temp["entry_date"])
        temp = temp.set_index("entry_date")

        result = temp.resample(period)["net_pnl"].agg(
            net_pnl="sum",
            trade_count="count"
        ).reset_index()

        result.columns = ["period", "net_pnl", "trade_count"]

        return result

    def _compuet_win_rate_by_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:

        if self._is_empty(df):
            return pd.DataFrame()

        temp = df.dropna(subset=[column]).copy()

        if temp.empty:
            return pd.DataFrame()

        def group_stats(group):

            total = len(group)
            wins = (group["outcome"] == "win").sum()
            losses = (group["outcome"] == "loss").sum()
            win_rate = (wins / total * 100) if total > 0 else 0.0
            avg_pnl = group["net_pnl"].mean()
            total_pnl = group["net_pnl"].sum()

            return pd.Series({
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "avg_pnl": round(avg_pnl, 2),
                "total_pnl": round(total_pnl, 2),
            })

        result = temp.groupby(column).apply(group_stats, include_groups=False).reset_index()
        result = result.sort_values("win_rate", ascending=False)

        return result

    def win_rate_by_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._compuet_win_rate_by_column(df, "strategy_name")

    def win_rate_by_emotional_state(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._compuet_win_rate_by_column(df, "emotional_state")

    def win_rate_by_market_condition(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._compuet_win_rate_by_column(df, "market_condition")

    def win_rate_by_timeframe(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._compuet_win_rate_by_column(df, "timeframe")

    def win_rate_by_day_of_week(self, df: pd.DataFrame) -> pd.DataFrame:

        if self._is_empty(df):
            return pd.DataFrame()    

        temp = df.copy()
        temp["entry_date"] = pd.to_datetime(temp["entry_date"])
        temp["day_of_week"] = temp["entry_date"].dt.day_name()

        result = self._compuet_win_rate_by_column(temp, "day_of_week")
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        if not result.empty:
            result["day_of_week"] = pd.Categorical(result["day_of_week"], categories=day_order, ordered=True)
            result = result.sort_values("day_of_week")

        return result

    def compute_rr_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:

        if self._is_empty(df):
            return {
                "avg_planned_rr": 0.0,
                "avg_actual_rr": 0.0,
                "rr_adherence_rate": 0.0,
                "cutting_winners_early": False,
                "letting_losers_run": False,
                "trades_with_rr_plan": 0
            }

        rr_df = df.dropna(subset=["planned_risk_per_share", "planned_reward_per_share"]).copy()

        trades_with_plan = len(rr_df)

        if trades_with_plan == 0:
            return {
                "avg_planned_rr": 0.0,
                "avg_actual_rr": 0.0,
                "rr_adherence_rate": 0.0,
                "cutting_winners_early": False,
                "letting_losers_run": False,
                "trades_with_rr_plan": 0
            }

        rr_df["planned_rr"] = (rr_df["planned_reward_per_share"] / rr_df["planned_risk_per_share"].replace(0, np.nan))

        avg_planned_rr = rr_df["planned_rr"].mean()
        avg_actual_rr = rr_df["actual_rr_ratio"].dropna().mean()

        rr_df["adhered"] = (abs(rr_df["actual_rr_ratio"] - rr_df["planned_rr"]) / rr_df["planned_rr"].replace(0, np.nan)) <= 0.20

        adherence_rate = rr_df["adhered"].mean() * 100

        cutting_winners_early = (avg_actual_rr < avg_planned_rr * 0.75 if pd.notna(avg_actual_rr) and pd.notna(avg_planned_rr) else False)

        return {
            "avg_planned_rr": round(avg_planned_rr, 2),
            "avg_actual_rr": round(float(avg_actual_rr), 2) if pd.notna(avg_actual_rr) else 0.0,
            "rr_adherence_rate": round(adherence_rate, 2),
            "cutting_winners_early": bool(cutting_winners_early),
            "letting_losers_run": False,
            "trades_with_rr_plan": trades_with_plan, 
        }

    def compute_drawdown(self, df:pd.DataFrame) -> Dict[str, Any]:

        if self._is_empty(df):
            return {
                "max_drawdown_pct": 0.0,
                "max_drawdown_dollars": 0.0,
                "current_drawdown_pct": 0.0,
                "drawdown_curve": pd.DataFrame(),
            }

        curve = self.compute_pnl_curve(df)

        if curve.empty:
            return {
                "max_drawdown_pct": 0.0,
                "max_drawdown_dollars": 0.0,
                "current_drawdown_pct": 0.0,
                "drawdown_curve": pd.DataFrame(),
            }

        cumulative = curve["cumulative_pnl"].values

        running_max = np.maximum.accumulate(cumulative)

        drawdown_dollars = cumulative - running_max

        drawdown_pct = np.where(running_max != 0, (drawdown_dollars / running_max) * 100, 0)

        max_drawdown_pct = float(np.min(drawdown_pct))

        max_drawdown_dollars = float(np.min(drawdown_dollars))

        current_drawdown_pct = float(drawdown_pct[-1])

        drawdown_curve = curve[["entry_date"]].copy()
        drawdown_curve["drawdown_pct"] = drawdown_pct
        drawdown_curve["drawdown_dollars"] = drawdown_dollars

        return {
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "max_drawdown_dollars": round(max_drawdown_dollars, 2),
            "current_drawdown_pct": round(current_drawdown_pct, 2),
            "drawdown_curve": drawdown_curve,
        }

    def compute_rolling_win_rate(
        self,
        df: pd.DataFrame,
        window: int = 10
    ) -> pd.DataFrame:

        if self._is_empty(df):
            return pd.DataFrame(
                columns = ["trade_number", "rolling_win_rate"]
            )
        temp = df.sort_values("entry_date").copy()

        temp["win_binary"] = temp["outcome"].map({
            "win": 1.0,
            "loss": 0.0,
            "breakeven": 0.5
        })

        temp["rolling_win_rate"] = (temp["win_binary"].rolling(window=window, min_periods=1).mean() * 100)

        temp["trade_number"] = range(1, len(temp) + 1)

        return temp[["trade_number", "rolling_win_rate", "entry_date"]]

    def compute_psychology_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:

        if self._is_empty(df):
            return {
                "emotion_win_rates": pd.DataFrame(),
                "confidence_analysis": pd.DataFrame(),
                "fomo_impact": {},
                "plan_adherence_impact": {},
                "avg_confidence_by_outcome": {},
            }

        emotion_win_rates = self.win_rate_by_emotional_state(df)

        conf_df = df.dropna(subset=["confidence_level"]).copy()

        if not conf_df.empty:
            confidence_analysis = self._compuet_win_rate_by_column(conf_df, "confidence_level")
        else:
            confidence_analysis = pd.DataFrame()

        avg_conf_wins = df[df["outcome"] == "win"]["confidence_level"].mean()
        avg_conf_losses = df[df["outcome"] == "loss"]["confidence_level"].mean()

        avg_confidence_by_outcome = {
            "avg_confidence_wins": round(float(avg_conf_wins), 2) if pd.notna(avg_conf_wins) else 0.0,
            "avg_confidence_losses": round(float(avg_conf_losses), 2) if pd.notna(avg_conf_losses) else 0.0
        }

        fomo_trades = df[df["fomo_factor"] == 1]
        non_fomo_trades = df[df["fomo_factor"] == 0]

        fomo_win_rate = (fomo_trades["outcome"] == "win").mean() * 100 if len(fomo_trades) > 0 else 0.0
        non_fomo_win_rate = (non_fomo_trades["outcome"] == "loss").mean() * 100 if len(non_fomo_trades) > 0 else 0.0

        fomo_avg_pnl = fomo_trades["net_pnl"].mean() if len(fomo_trades) > 0 else 0.0
        non_fomo_avg_pnl = non_fomo_trades["net_pnl"].mean() if len(non_fomo_trades) > 0 else 0.0

        fomo_impact = {
            "fomo_trade_count": len(fomo_trades),
            "non_fomo_trade_count": len(non_fomo_trades),
            "fomo_win_rate": round(fomo_win_rate, 2),
            "non_fomo_win_rate": round(non_fomo_win_rate, 2),
            "fomo_avg_pnl": round(float(fomo_avg_pnl), 2),
            "non_fomo_avg_pnl": round(float(non_fomo_avg_pnl), 2),
            "fomo_cost": round(float(non_fomo_avg_pnl - fomo_avg_pnl), 2),
        }

        planned = df[df["followed_plan"] == 1]
        unplanned = df[df["followed_plan"] == 0]

        plan_win_rate = (planned["outcome"] == "win").mean() * 100  if len(planned) > 0 else 0.0 
        no_plan_win_rate = (planned["outcome"] == "loss").mean() * 100  if len(unplanned) > 0 else 0.0

        plan_adherence_impact = {
            "planned_trade_count": len(planned),
            "unplanned_trade_count": len(unplanned),
            "planned_win_rate": round(plan_win_rate, 2),
            "unplanned_win_rate": round(no_plan_win_rate, 2),
            "planned_avg_pnl": round(float(planned["net_pnl"].mean()), 2) if len(planned) > 0 else 0.0,
            "unplanned_avg_pnl": round(float(unplanned["net_pnl"].mean()), 2) if len(unplanned) > 0 else 0.0,
        } 

        return {
            "emotion_win_rates": emotion_win_rates,
            "confidence_analysis": confidence_analysis,
            "fomo_impact": fomo_impact,
            "plan_adherence_impact": plan_adherence_impact,
            "avg_confidence_by_outcome": avg_confidence_by_outcome,
        }

    def build_ai_context(self, df: pd.DataFrame) -> Dict[str, Any]:

        if self._is_empty(df):
            return {"error": "No trade data available for analysis"}

        summary = self.compute_summary_metrics(df)
        rr = self.compute_rr_analysis(df)
        drawdown = self.compute_drawdown(df)
        psychology = self.compute_psychology_metrics(df)

        emotion_wr = {}
        if not psychology["emotion_win_rates"].empty:
            for _, row in psychology["emotion_win_rates"].iterrows():
                emotion_wr[row["emotional_state"]] = {
                    "win_rate": row["win_rate"],
                    "total_trades": row["total_trades"],
                    "avg_pnl": row["avg_pnl"],
                }
        
        strategy_wr = {}
        strategy_df = self.win_rate_by_strategy(df)
        if not strategy_df.empty:
            for _, row in strategy_df.iterrows():
                strategy_wr[row["strategy_name"]] = {
                    "win_rate": row["win_rate"],
                    "total_trades": row["total_trades"],
                    "avg_pnl": row["avg_pnl"],
                }

        return {
            "summary": summary,
            "rr_analysis": rr,
            "max_drawdown_pct": drawdown["max_drawdown_pct"],
            "emotion_win_rates": emotion_wr,
            "strategy_win_rates": strategy_wr,
            "fomo_impact": psychology["fomo_impact"],
            "plan_adherence": psychology["plan_adherence_impact"],
            "avg_confidence_by_outcome": psychology["avg_confidence_by_outcome"],
        }