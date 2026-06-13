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

        total_commissions = df["commission"].sum()

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
        risk_metrics = self.compute_risk_metrics_summary(df)
        behavioral = self.compute_behavioral_correlations(df)

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
            "risk_metrics": risk_metrics,
            "max_drawdown_pct": drawdown["max_drawdown_pct"],
            "emotion_win_rates": emotion_wr,
            "strategy_win_rates": strategy_wr,
            "fomo_impact": psychology["fomo_impact"],
            "plan_adherence": psychology["plan_adherence_impact"],
            "avg_confidence_by_outcome": psychology["avg_confidence_by_outcome"],
            "behavioral_correlations": behavioral,
        }

    def compute_sharpe_ratio(self, df: pd.DataFrame, risk_free_rate: float = 0.05) -> Dict[str, Any]:

        if self._is_empty(df) or len(df) < 3:
            
            return {
                "sharpe_ratio": 0.0,
                "annualized_return_pct": 0.0,
                "return_volatility": 0.0,
                "trades_analyzed": 0,
                "interpretation": "Insufficient trades for Sharpe calculation"
            }

        returns = df["return_pct"].dropna()

        if len(returns) < 3:
            return{
                "sharpe_ratio": 0.0,
                "annualized_return_pct": 0.0,
                "return_volatility": 0.0,
                "trades_analyzed": 0,
                "interpretation": "Insufficient trades for Sharpe calculation"
            }

        mean_return = returns.mean()
        std_return = returns.std()

        df_dated = df.dropna(subset=["entry_date", "exit_date"]).copy()

        if not df_dated.empty:

            df_dated["holding_days"] = (pd.to_datetime(df_dated["exit_date"]) - pd.to_datetime(df_dated["entry_date"])).dt.days.clip(lower=1)

            avg_holding_days = df_dated["holding_days"].mean()
        else:
            avg_holding_days = 1.0

        trades_per_year = 252.0 / max(avg_holding_days, 1.0)

        annualized_return = mean_return * trades_per_year
        annualized_std = std_return * np.sqrt(trades_per_year)

        risk_free_pct = risk_free_rate * 100

        if annualized_std > 0:

            sharpe = (annualized_return - risk_free_pct) / annualized_std
        
        else:

            sharpe = 0.0

        if sharpe < 0:
            interpretation = "Negative — returns don't justify the risk"
        elif sharpe < 1.0:
            interpretation = "Below 1.0 — poor risk-adjusted performance"
        elif sharpe < 2.0:
            interpretation = "1.0 – 2.0 — good risk-adjusted performance"
        elif sharpe < 3.0:
            interpretation = "2.0 – 3.0 — excellent, professional level"
        else:
            interpretation = "Above 3.0 — exceptional"

        return {
            "sharpe_ratio": round(sharpe, 3),
            "annualized_return_pct": round(annualized_return, 2),
            "return_volatility": round(annualized_std, 2),
            "avg_holding_days": round(avg_holding_days, 1),
            "trades_per_year_estimate": round(trades_per_year, 1),
            "trades_analyzed": len(returns),
            "interpretation": interpretation,
        }

    def compute_calmar_ratio(self, df: pd.DataFrame) -> Dict[str, Any]:

        if self._is_empty(df) or len(df) < 2:
            return {
                "calmar_ratio": 0.0,
                "annualized_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "interpretation": "Insufficient data"
            }

        sharpe_data = self.compute_sharpe_ratio(df)
        annualized_return = sharpe_data["annualized_return_pct"]

        dd_data = self.compute_drawdown(df)
        max_dd = abs(dd_data["max_drawdown_pct"])

        if max_dd > 0:
            calmar = annualized_return / max_dd
        else:
            calmar = float("inf") if annualized_return > 0 else 0.0

        if calmar == float("inf"):
            interpretation = "No drawdown recorded — insufficient history"
        elif calmar < 0:
            interpretation = "Negative — system is losing money"
        elif calmar < 1.0:
            interpretation = "Below 1.0 — drawdowns exceed annual returns"
        elif calmar < 3.0:
            interpretation = "1.0 – 3.0 — acceptable risk management"
        else:
            interpretation = "Above 3.0 — strong risk management"

        return {
            "calmar_ratio": round(calmar, 3) if calmar != float("inf") else 0.0,
            "annualized_return_pct": round(annualized_return, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "interpretation": interpretation,
        }
    
    def compute_risk_metrics_summary(self, df: pd.DataFrame) -> Dict[str, Any]:

        sharpe = self.compute_sharpe_ratio(df)
        calmar = self.compute_calmar_ratio(df)
        drawdown = self.compute_drawdown(df)

        return {
            "sharpe_ratio": sharpe["sharpe_ratio"],
            "sharpe_interpretation": sharpe["interpretation"],
            "calmar_ratio": calmar["calmar_ratio"],
            "calmar_interpretation": calmar["interpretation"],
            "max_drawdown_pct": drawdown["max_drawdown_pct"],
            "max_drawdown_dollars": drawdown["max_drawdown_dollars"],
            "current_drawdown_pct": drawdown["current_drawdown_pct"],
            "return_volatility": sharpe["return_volatility"],
            "avg_holding_days": sharpe.get("avg_holding_days", 0.0),
        }

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:

        if self._is_empty(df):
            return df

        enriched = df.copy()

        enriched["entry_date_dt"] = pd.to_datetime(enriched["entry_date"])

        enriched["entry_hour"] = enriched["entry_date_dt"].dt.hour
        enriched["entry_day_of_week_num"] = enriched["entry_date"].dt.dayofweek
        enriched["entry_day_name"] = enriched["entry_date_dt"].dt.day_name()
        enriched["entry_month"] = enriched["entry_date_dt"].dt.month

        enriched["is_monday_trade"] = (enriched["entry_day_of_week_num"] == 0).astype(int)
        enriched["is_friday_trade"] = (enriched["entry_day_of_week_num"] == 4).astype(int)

        enriched["is_morning_trade"] = (enriched["entry_hour"] < 10).astype(int)

        has_exit = enriched["exit_date"].notna()
        enriched["holding_days"] = np.nan

        if has_exit.any():

            exit_dates = pd.to_datetime(enriched.loc[has_exit, "exit_date"])
            entry_dates = pd.to_datetime(enriched.loc[has_exit, "entry_date_dt"])
            enriched.loc[has_exit, "holding_days"] = (exit_dates - entry_dates).dt.days.clip(lower = 0)

        enriched["position_size"] = (enriched["entry_price"] * enriched["quantity"]).round(2)

        has_stop = enriched["planned_risk_per_share"].notna()
        enriched["risk_amount"] = np.nan

        if has_stop.any():
            enriched.loc[has_stop, "risk_amount"] = (enriched.loc[has_stop, "planned_risk_per_share"] * enriched.loc[has_stop, "quantity"]).round(2)

        has_reward = enriched["planned_reward_per_share"].notna()
        enriched["reward_amount"] = np.nan

        if has_reward.any():    
            enriched.loc[has_reward, "reward_amount"] = (enriched.loc[has_reward, "planned_reward_per_share"] * enriched.loc[has_reward, "quantity"]).round(2)

        enriched["win_binary"] = enriched["outcome"].map({
            "win": 1.0,
            "loss": 0.0,
            "breakeven": 0.5
        })

        enriched["high_confidence"] = (enriched["confidence_level"] >= 8).astype(int)

        median_conf = enriched["confidence_level"].median()
        enriched["above_median_confidence"] = (enriched["confidence_level"] > median_conf).astype(int)

        enriched["is_impulsive"] = ((enriched["fomo_factor"] == 1) | (enriched["followed_plan"] == 0)).astype(int)
        enriched["is_disciplined"] = ((enriched["stop_loss_price"].notna()) & (enriched["followed_plan"] == 1) & (enriched["fomo_factor"] == 0)).astype(int)

        calm_states = ["calm", "neutral", "confident"]
        enriched["is_emotional"] = (~enriched["emotional_state"].isin(calm_states)).astype(int)

        enriched["market_aligned"] = ((enriched["direction"] == "long") & (enriched["spy_direction"] == "up")).astype(int)

        enriched = enriched.drop(columns=["entry_date_dt"], errors="ignore")

        logger.info(
            f"Feature engineering: {len(df.columns)} → "
            f"{len(enriched.columns)} columns"
        )

        return enriched

    def compute_feature_correlations(self, df: pd.DataFrame) -> pd.DataFrame:

        if self._is_empty(df) or len(df) < 5:
            return pd.DataFrame(columns=["feature", "correlation", "strength", "direction"])

        enriched = self.engineer_features(df)

        correlation_features = [
            "confidence_level",
            "entry_hour",
            "entry_day_of_week_num",
            "entry_month",
            "holding_days",
            "position_size",
            "risk_amount",
            "high_confidence",
            "above_median_confidence",
            "is_impulsive",
            "is_disciplined",
            "is_emotional",
            "is_morning_trade",
            "is_monday_trade",
            "is_friday_trade",
            "market_aligned",
            "fomo_factor",
            "followed_plan",
        ]

        availabel = [f for f in correlation_features if f in enriched.columns]

        if "return_pct" not in enriched.columns or not availabel:
            return pd.DataFrame()

        results = []
        target = enriched["return_pct"].dropna()

        for feature in availabel:
            feature_series = enriched[feature].dropna()

            aligned = pd.concat([target, feature_series], axis = 1).dropna()

            if len(aligned) < 5:
                continue

            if aligned[feature].nunique() <= 1:
                continue

            corr = aligned["return_pct"].corr(aligned[feature])

            if pd.isna(corr):
                continue

            abs_corr = abs(corr)
            if abs_corr >= 0.5:
                strength = "strong"
            elif abs_corr >= 0.3:
                strength = "moderate"
            elif abs_corr >= 0.1:
                strength = "weak"
            else:
                strength = "negligible"

            direction = "positive" if corr > 0 else "negative"

            results.append({
                "feature": feature,
                "correlation": round(corr, 4),
                "abs_correlation": round(abs_corr, 4),
                "strength": strength,
                "direction": direction,
            })

        if not results:
            return pd.DataFrame()

        result_df = pd.DataFrame(results)

        result_df = result_df.sort_values("abs_correlation", ascending=False).reset_index(drop=True)

        return result_df

    def compute_behavioral_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:

        if self._is_empty(df) or len(df) < 3:
            return {
                "findings": [],
                "most_predictive_feature": None,
                "top_correlation": 0.0,
            }

        enriched = self.engineer_features(df)
        findings = []

        impulsive = enriched[enriched["is_impulsive"] == 1]
        disciplined = enriched[enriched["is_impulsive"] == 0]

        if len(impulsive) >= 2 and len(disciplined) >= 2:
            imp_wr = (impulsive["outcome"] == "win").mean() * 100
            disc_wr = (disciplined["outcome"] == "win").mean() * 100
            imp_pnl = impulsive["net_pnl"].mean()
            disc_pnl = disciplined["net_pnl"].mean()

            findings.append({
                "factor": "impulsive_vs_disciplined",
                    "label": "Impulsive vs Disciplined Trades",
                    "impulsive_win_rate": round(imp_wr, 1),
                    "disciplined_win_rate": round(disc_wr, 1),
                    "impulsive_avg_pnl": round(float(imp_pnl), 2),
                    "disciplined_avg_pnl": round(float(disc_pnl), 2),
                    "win_rate_gap": round(disc_wr - imp_wr, 1),
                    "insight": (
                        f"Disciplined trades win {round(disc_wr - imp_wr, 1)}% more often than impulsive trades"
                    )
            })

        aligned = enriched[enriched["market_aligned"] == 1]
        against = enriched[enriched["market_aligned"] == 0]

        if len(aligned) >= 2 and len(against) >= 2:
            al_wr = (aligned["outcome"] == "win").mean() * 100
            ag_wr = (against["outcome"] == "win").mean() * 100

            findings.append({
                    "factor": "market_alignment",
                    "label": "Aligned vs Against Market Direction",
                    "aligned_win_rate": round(al_wr, 1),
                    "against_win_rate": round(ag_wr, 1),
                    "win_rate_gap": round(al_wr - ag_wr, 1),
                    "insight": (
                        f"Trades aligned with market direction win {round(al_wr - ag_wr, 1)}% more often"
                    )
                })

        morning = enriched[enriched["is_morning_trade"] == 1]
        non_morning = enriched[enriched["is_morning_trade"] == 0]

        if len(morning) >= 2 and len(non_morning) >= 2:
            m_wr = (morning["outcome"] == "win").mean() * 100
            nm_wr = (non_morning["outcome"] == "win").mean() * 100
            m_pnl = morning["net_pnl"].mean()
            nm_pnl = non_morning["net_pnl"].mean()

            findings.append({
                "factor": "morning_trade",
                "label": "Morning Trades vs Rest of Day",
                "morning_win_rate": round(m_wr, 1),
                "non_morning_win_rate": round(nm_wr, 1),
                "morning_avg_pnl": round(float(m_pnl), 2),
                "non_morning_avg_pnl": round(float(nm_pnl), 2),
                "insight": (
                    f"Morning trades (before 10am) have {round(m_wr - nm_wr, 1)}% different win rate vs rest of day"
                )
            })

        high_conf = enriched[enriched["high_confidence"] == 1]
        normal_conf = enriched[enriched["high_confidence"] == 0]

        if len(high_conf) >= 2 and len(normal_conf) >= 2:
            hc_wr = (high_conf["outcome"] == "win").mean() * 100
            nc_wr = (normal_conf["outcome"] == "win").mean() * 100

            overconfidence_detected = hc_wr < nc_wr

            findings.append({
                "factor": "high_confidence_trap",
                "label": "High Confidence (8+) vs Normal Confidence",
                "high_conf_win_rate": round(hc_wr, 1),
                "normal_conf_win_rate": round(nc_wr, 1),
                "overconfidence_detected": overconfidence_detected,
                "insight": (
                    "Overconfidence pattern detected — high confidence trades underperform" if overconfidence_detected else "Confidence calibration looks healthy"
                )
            })

        corr_df = self.compute_feature_correlations(enriched)
        if not corr_df.empty:
            top_row = corr_df.iloc[0]
            most_predictive = top_row["feature"]
            top_correlation = top_row["correlation"]
        else:
            most_predictive = None
            top_correlation = 0.0

        return {
            "findings": findings,
            "most_predictive_feature": most_predictive,
            "top_correlation": float(top_correlation),
            "total_features_analyzed": len(corr_df) if not corr_df.empty else 0,
        }