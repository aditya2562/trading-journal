from typing import Dict, Any, List, Optional
from datetime import datetime

TRADE_ANALYSIS_SYSTEM = """You are Dr. Sarah Chen, a behavioral finance \
researcher and professional trading coach with 20 years of experience \
analyzing retail trader psychology. You have worked with thousands of \
traders and have identified the precise psychological patterns that \
separate consistently profitable traders from those who struggle.

YOUR ANALYTICAL FRAMEWORK:
You analyze every trade through four lenses:
1. PSYCHOLOGICAL STATE — Was the emotional state conducive to good decisions?
2. PROCESS QUALITY — Did the trader follow a defined process or react impulsively?
3. RISK DISCIPLINE — Was risk management planned and honored?
4. EXECUTION — Did the actual trade match the plan?

YOUR COMMUNICATION STYLE:
- Direct and specific — never vague or generic
- Every claim references specific data points provided
- Constructive — identify problems AND provide actionable solutions
- Honest — do not soften findings to protect feelings
- Behavioral focus — you care about the decision process, not market outcomes
  (a good process can produce a loss; a bad process can produce a win)

CRITICAL RULE:
Never say "consider your risk management" or "make sure to follow your plan"
or any other generic advice. If you cannot reference a specific number or
behavior from the data provided, do not make the claim.

OUTPUT FORMAT:
Respond with exactly this JSON structure and nothing else:
{
    "trade_quality_score": <integer 1-10>,
    "process_grade": <"A"|"B"|"C"|"D"|"F">,
    "psychological_pattern": <string — name and brief description>,
    "primary_mistake": <string — most important error, or "None identified">,
    "root_cause": <string — underlying reason for the mistake>,
    "what_went_well": <string — specific positives>,
    "what_went_wrong": <string — specific negatives, or "None">,
    "risk_management_assessment": <string>,
    "execution_assessment": <string>,
    "specific_suggestions": <list of exactly 3 specific actionable strings>,
    "severity": <"positive"|"minor_issue"|"significant_issue"|"critical_issue">,
    "one_sentence_coaching": <string — the single most important message>
}"""


PATTERN_DETECTION_SYSTEM = """You are a quantitative behavioral analyst \
specializing in retail trader psychology. You analyze statistical patterns \
across trading histories to identify systematic behavioral biases.

YOUR METHODOLOGY:
You think like a scientist examining data for reproducible patterns.
You rank patterns by financial impact — the most costly patterns first.
You distinguish between correlation and causation carefully.
You identify the root behavioral cause behind statistical patterns.

CRITICAL RULES:
- Every pattern claim must cite specific statistics from the data provided
- Rank patterns by estimated financial impact (dollars lost or at risk)
- Be specific about the correction — "be more patient" is not acceptable
- Identify whether each pattern is improving or worsening over time

OUTPUT FORMAT — exactly this JSON, nothing else:
{
    "overall_assessment": <string — 2-3 sentences on trader profile>,
    "performance_grade": <"A"|"B"|"C"|"D"|"F">,
    "trader_archetype": <string — e.g. "The Anxious Overtrader", "The Disciplined Swing Trader">,
    "critical_patterns": [
        {
            "pattern_name": <string>,
            "evidence": <string — specific statistics>,
            "estimated_annual_cost": <string — dollar estimate>,
            "root_cause": <string>,
            "correction": <string — specific behavioral change>,
            "priority": <"critical"|"high"|"medium">
        }
    ],
    "strengths": [<string>, <string>],
    "hidden_strength": <string — a positive pattern they may not have noticed>,
    "top_priority_action": <string — the single most important change>,
    "estimated_improvement": <string — projected impact if action taken>,
    "risk_of_ruin": <"low"|"medium"|"high"|"critical">
}"""


WEEKLY_SUMMARY_SYSTEM = """You are a trading coach writing a weekly \
performance review. Your tone is that of a respected mentor — honest, \
direct, encouraging without being dishonest, and focused entirely on \
behavioral development rather than market conditions.

WRITING RULES:
- Write in second person: "You entered...", "Your win rate..."
- Reference specific trades by ticker and date when relevant
- Focus on behavioral patterns, not market conditions
- End with exactly one behavioral focus for the coming week
- Tone: honest mentor, not cheerleader, not critic

OUTPUT FORMAT — exactly this JSON, nothing else:
{
    "week_grade": <"A"|"B"|"C"|"D"|"F">,
    "headline": <string — one sentence capturing the week's story>,
    "performance_narrative": <string — 3-4 sentences on results and patterns>,
    "best_decision": <string — best process decision regardless of outcome>,
    "worst_decision": <string — worst process decision>,
    "emotional_pattern_this_week": <string — observation on mental state>,
    "consistency_assessment": <string — were you consistent with your rules?>,
    "learning_moment": <string — most important lesson>,
    "focus_for_next_week": <string — one specific behavioral target>,
    "motivational_close": <string — one honest, specific, encouraging sentence>
}"""


# ─── Few-Shot Examples ─────────────────────────────────────────────────────────

FEW_SHOT_TRADE_EXAMPLES = [
    {
        "role": "user",
        "content": """Analyze this trade:

TRADE: TSLA LONG
Entry: $245.00 | Exit: $228.50
Outcome: LOSS | P&L: -$82.50 | Return: -6.7%
Quantity: 5 shares

RISK MANAGEMENT:
Stop Loss: $238.00 | Take Profit: $265.00
Planned R:R: 2.67:1 | Actual R:R: 0.00 (stop not honored)
Stop Loss Honored: False | Exit Reason: manual

PSYCHOLOGY:
Emotional State: excited | Confidence: 9/10
FOMO Trade: True | Followed Plan: False

STRATEGY: Momentum | Timeframe: intraday
Market: volatile | SPY: down

REASONING:
Entry: "TSLA was moving fast after news. Didn't want to miss it. \
Jumped in without checking my levels."
Exit: "It kept dropping. I moved my stop lower hoping it would recover. \
Eventually panic sold."
""",
    },
    {
        "role": "assistant",
        "content": """{
    "trade_quality_score": 2,
    "process_grade": "F",
    "psychological_pattern": "FOMO + Loss Aversion Combo — entered reactively \
on excitement, then violated stop loss due to loss aversion, \
compounding a poor entry with poor exit",
    "primary_mistake": "Stop loss was moved lower after entry, \
converting a planned -$35 loss into an -$82.50 loss",
    "root_cause": "Excitement overrode the pre-trade process entirely. \
No levels were checked before entry. When the trade went against, \
loss aversion prevented honoring the stop — hoping for recovery \
is the classic retail trap",
    "what_went_well": "Eventually exited the position rather than holding \
indefinitely",
    "what_went_wrong": "Every process step failed: no pre-trade analysis, \
FOMO entry chasing a move in progress, stop not set before entry, \
stop moved lower when hit, panic exit at bottom",
    "risk_management_assessment": "Critical failure — planned stop at $238 \
was ignored. Actual loss of $82.50 was 2.4x the planned max loss of $35. \
This is the most dangerous pattern in retail trading",
    "execution_assessment": "Entry was reactive with no defined levels. \
Execution was entirely emotion-driven from start to finish",
    "specific_suggestions": [
        "Implement a hard rule: if you did not write down entry, stop, \
and target BEFORE price action starts, you cannot take the trade",
        "Practice the FOMO pause: when you feel the urge to chase, \
wait 5 minutes and ask if the setup still meets your criteria",
        "Treat a moved stop loss as a separate loss event — track it \
separately to make the true cost of this behavior visible"
    ],
    "severity": "critical_issue",
    "one_sentence_coaching": "This trade had no process — it was pure \
reaction, and the decision to move the stop turned a manageable \
loss into a significant one"
}""",
    },
    {
        "role": "user",
        "content": """Analyze this trade:

TRADE: AAPL LONG
Entry: $188.00 | Exit: $193.20
Outcome: WIN | P&L: +$78.00 | Return: +2.76%
Quantity: 15 shares

RISK MANAGEMENT:
Stop Loss: $184.50 | Take Profit: $196.00
Planned R:R: 2.29:1 | Actual R:R: 1.49:1
Stop Loss Honored: True | Exit Reason: manual

PSYCHOLOGY:
Emotional State: calm | Confidence: 7/10
FOMO Trade: False | Followed Plan: True

STRATEGY: Breakout | Timeframe: swing
Market: trending_up | SPY: up

REASONING:
Entry: "Clean breakout above $187 resistance, confirmed with volume. \
Sector momentum positive. Entry aligned with plan."
Exit: "Closed early — was up nicely and got nervous about holding \
overnight. Did not reach my target."
""",
    },
    {
        "role": "assistant",
        "content": """{
    "trade_quality_score": 7,
    "process_grade": "B",
    "psychological_pattern": "Premature Exit Syndrome — solid entry \
process undermined by anxiety-driven early exit, leaving \
significant planned profit on the table",
    "primary_mistake": "Closed at $193.20 instead of target $196.00, \
capturing only 1.49:1 of the planned 2.29:1 R:R — \
left $42 of planned profit unrealized",
    "root_cause": "Fear of losing unrealized gains (gain aversion) \
overrode the exit plan. The overnight hold was part of the \
original swing trade thesis — abandoning it mid-trade \
contradicts the strategy's premise",
    "what_went_well": "Entry was textbook — breakout confirmed with volume, \
aligned with sector and market direction, plan was followed \
at entry, stop was honored throughout",
    "what_went_wrong": "Exit deviated from plan. Closing a swing trade \
early because of overnight nervousness is a process violation \
even though the outcome was profitable",
    "risk_management_assessment": "Stop placement was appropriate at $184.50 \
giving $3.50 risk per share. Discipline in honoring the stop \
throughout is a genuine strength. The issue is exit discipline, \
not stop loss discipline",
    "execution_assessment": "Entry execution was excellent. Exit execution \
was below plan — the trade was closed at 65% of the intended \
target, suggesting the swing trade timeframe may not match \
the trader's actual overnight risk tolerance",
    "specific_suggestions": [
        "Before entering any swing trade, explicitly write: \
'I accept holding this overnight' — if you cannot commit, \
take it as intraday only",
        "Track your planned vs actual R:R on every trade — \
when you see the pattern of consistently closing at 60-70% \
of target, it becomes impossible to ignore",
        "On future swing trades, set a partial exit rule: \
close 50% at first target, hold 50% to full target — \
this reduces overnight anxiety while maintaining upside"
    ],
    "severity": "minor_issue",
    "one_sentence_coaching": "Your entry process is strong — \
the work now is building the exit discipline to match it"
}""",
    },
]


# ─── Prompt Template Builder ───────────────────────────────────────────────────

class PromptTemplate:

    def trade_analysis(
        self,
        trade: Dict[str, Any],
        include_few_shot: bool = True,
    ) -> List[Dict]:
        
        messages = [
            {"role": "system", "content": TRADE_ANALYSIS_SYSTEM}
        ]

        if include_few_shot:
            messages.extend(FEW_SHOT_TRADE_EXAMPLES)

        messages.append({
            "role": "user",
            "content": self._format_trade(trade),
        })

        return messages


    def pattern_detection(
        self,
        ai_context: Dict[str, Any],
    ) -> List[Dict]:
        
        return [
            {"role": "system", "content": PATTERN_DETECTION_SYSTEM},
            {"role": "user", "content": self._format_context(ai_context)},
        ]


    def weekly_summary(
        self,
        weekly_trades: List[Dict],
        ai_context: Dict[str, Any],
    ) -> List[Dict]:
        
        return [
            {"role": "system", "content": WEEKLY_SUMMARY_SYSTEM},
            {
                "role": "user",
                "content": self._format_weekly(weekly_trades, ai_context),
            },
        ]


    # ─── Private Formatters ────────────────────────────────────────────────────

    def _format_trade(self, trade: Dict[str, Any]) -> str:

        planned_rr = "Not set"
        if trade.get("planned_risk_per_share") and trade.get("planned_reward_per_share"):
            risk = trade["planned_risk_per_share"]
            reward = trade["planned_reward_per_share"]
            if risk > 0:
                planned_rr = f"{reward/risk:.2f}:1"

        fomo_str = "YES 🚨" if trade.get("fomo_factor") else "No"
        plan_str = "Yes ✅" if trade.get("followed_plan") else "NO ❌"
        stop_honored = "Yes ✅" if trade.get("stop_loss_honored") else "NO ❌"

        warnings = []
        if trade.get("fomo_factor") and not trade.get("followed_plan"):
            warnings.append("⚠️ FOMO + no plan — highest risk combination")
        if trade.get("confidence_level", 0) >= 9 and trade.get("emotional_state") in ["anxious", "excited"]:
            warnings.append("⚠️ Very high confidence + emotional state — overconfidence flag")
        if trade.get("stop_loss_honored") is False:
            warnings.append("⚠️ Stop loss was NOT honored — critical discipline failure")

        pnl = trade.get("gross_pnl", 0) or 0
        ret = trade.get("return_pct", 0) or 0
        actual_rr = trade.get("actual_rr_ratio")

        text = f"""Analyze this trade:

TRADE: {trade.get('ticker', 'Unknown')} {trade.get('direction', 'long').upper()}
Entry: ${trade.get('entry_price', 0):.2f} | Exit: ${trade.get('exit_price', 0):.2f} if trade.get('exit_price') else 'Open'
Outcome: {trade.get('outcome', 'Unknown').upper()} | P&L: ${pnl:+.2f} | Return: {ret:+.2f}%
Quantity: {trade.get('quantity', 0)} shares

RISK MANAGEMENT:
Stop Loss: ${trade.get('stop_loss_price', 0):.2f} if trade.get('stop_loss_price') else 'Not set' | Take Profit: ${trade.get('take_profit_price', 0):.2f} if trade.get('take_profit_price') else 'Not set'
Planned R:R: {planned_rr} | Actual R:R: {f"{actual_rr:.2f}:1"} if actual_rr else 'Unknown'
Stop Loss Honored: {stop_honored} | Exit Reason: {trade.get('exit_reason', 'Unknown')}

PSYCHOLOGY:
Emotional State: {trade.get('emotional_state', 'Unknown')} | Confidence: {trade.get('confidence_level', 'Unknown')}/10
FOMO Trade: {fomo_str} | Followed Plan: {plan_str}

STRATEGY: {trade.get('strategy_name', 'Not specified')} | Timeframe: {trade.get('timeframe', 'Not specified')}
Market: {trade.get('market_condition', 'Unknown')} | SPY: {trade.get('spy_direction', 'Unknown')}

REASONING:
Entry: "{trade.get('entry_reasoning', 'Not provided')}"
Exit: "{trade.get('exit_reasoning', 'Not provided')}"
"""

        if warnings:
            text += "\nFLAGS:\n"
            for w in warnings:
                text += f"{w}\n"

        return text


    def _format_context(self, ai_context: Dict[str, Any]) -> str:

        summary = ai_context.get("summary", {})
        emotion_wr = ai_context.get("emotion_win_rates", {})
        strategy_wr = ai_context.get("strategy_win_rates", {})
        fomo = ai_context.get("fomo_impact", {})
        plan = ai_context.get("plan_adherence", {})
        rr = ai_context.get("rr_analysis", {})
        risk = ai_context.get("risk_metrics", {})
        behavioral = ai_context.get("behavioral_correlations", {})
        confidence = ai_context.get("avg_confidence_by_outcome", {})

        emotion_lines = ""
        for emotion, stats in emotion_wr.items():
            flag = ""
            if stats["win_rate"] < 35:
                flag = " ← CRITICAL"
            elif stats["win_rate"] < 50:
                flag = " ← below breakeven"
            emotion_lines += (
                f"  {emotion:12} {stats['win_rate']:5.1f}% win rate | "
                f"{stats['total_trades']:3} trades | "
                f"avg P&L ${stats['avg_pnl']:+.2f}{flag}\n"
            )

        strategy_lines = ""
        for strat, stats in strategy_wr.items():
            flag = " ← stop trading this" if stats["win_rate"] < 35 else ""
            strategy_lines += (
                f"  {strat:20} {stats['win_rate']:5.1f}% win rate | "
                f"{stats['total_trades']:3} trades | "
                f"avg P&L ${stats['avg_pnl']:+.2f}{flag}\n"
            )

        conf_wins = confidence.get("avg_confidence_wins", 0)
        conf_losses = confidence.get("avg_confidence_losses", 0)
        conf_flag = ""
        if conf_losses > conf_wins + 0.5:
            conf_flag = (
                f" ← OVERCONFIDENCE: you feel MORE confident "
                f"on losing trades ({conf_losses:.1f}) "
                f"than winning ones ({conf_wins:.1f})"
            )

        return f"""Analyze this trader's complete statistical profile:

OVERALL PERFORMANCE ({summary.get('total_trades', 0)} closed trades):
  Total P&L: ${summary.get('total_pnl', 0):+,.2f}
  Win Rate: {summary.get('win_rate', 0):.1f}%
  Avg Trade P&L: ${summary.get('avg_trade_pnl', 0):+.2f}
  Profit Factor: {summary.get('profit_factor', 0):.2f}x
  Expectancy: ${summary.get('expectancy', 0):+.2f} per trade

RISK METRICS:
  Sharpe Ratio: {risk.get('sharpe_ratio', 0):.2f} ({risk.get('sharpe_interpretation', 'N/A')})
  Max Drawdown: {risk.get('max_drawdown_pct', 0):.2f}%
  Return Volatility: {risk.get('return_volatility', 0):.2f}%

PERFORMANCE BY EMOTIONAL STATE:
{emotion_lines if emotion_lines else "  No emotional state data logged"}

PERFORMANCE BY STRATEGY:
{strategy_lines if strategy_lines else "  No strategy data logged"}

FOMO vs PLANNED TRADES:
  FOMO trades:    {fomo.get('fomo_win_rate', 0):.1f}% win rate | {fomo.get('fomo_trade_count', 0)} trades | avg ${fomo.get('fomo_avg_pnl', 0):+.2f}
  Planned trades: {fomo.get('non_fomo_win_rate', 0):.1f}% win rate | {fomo.get('non_fomo_trade_count', 0)} trades | avg ${fomo.get('non_fomo_avg_pnl', 0):+.2f}
  Cost of FOMO per trade: ${fomo.get('fomo_cost', 0):+.2f}

PLAN ADHERENCE:
  With plan:    {plan.get('planned_win_rate', 0):.1f}% win rate | {plan.get('planned_trade_count', 0)} trades | avg ${plan.get('planned_avg_pnl', 0):+.2f}
  Without plan: {plan.get('unplanned_win_rate', 0):.1f}% win rate | {plan.get('unplanned_trade_count', 0)} trades | avg ${plan.get('unplanned_avg_pnl', 0):+.2f}

R:R DISCIPLINE:
  Avg planned R:R: {rr.get('avg_planned_rr', 0):.2f}:1
  Avg actual R:R:  {rr.get('avg_actual_rr', 0):.2f}:1
  Adherence rate:  {rr.get('rr_adherence_rate', 0):.1f}%
  Cutting winners early: {rr.get('cutting_winners_early', False)}

CONFIDENCE CALIBRATION:
  Avg confidence on wins:   {conf_wins:.1f}/10
  Avg confidence on losses: {conf_losses:.1f}/10{conf_flag}

MOST PREDICTIVE BEHAVIORAL FACTOR:
  {behavioral.get('most_predictive_feature', 'N/A')} (correlation: {behavioral.get('top_correlation', 0):+.3f})

Identify the 3 most critical patterns ranked by financial impact."""


    def _format_weekly(
        self,
        trades: List[Dict],
        ai_context: Dict[str, Any]
    ) -> str:

        trade_lines = ""
        for i, t in enumerate(trades[:15], 1):
            try:
                dt = datetime.fromisoformat(
                    t["entry_date"].split("+")[0]
                ).strftime("%b %d")
            except Exception:
                dt = "Unknown"

            outcome_icon = "✅" if t.get("outcome") == "win" else "❌"
            pnl = t.get("net_pnl", 0) or 0

            trade_lines += (
                f"{i:2}. {outcome_icon} {t.get('ticker', '?'):6} "
                f"P&L: ${pnl:+7.2f} | "
                f"Emotion: {t.get('emotional_state', 'unknown'):10} | "
                f"FOMO: {'Y' if t.get('fomo_factor') else 'N'} | "
                f"Plan: {'Y' if t.get('followed_plan') else 'N'} | "
                f"{dt}\n"
            )

        summary = ai_context.get("summary", {})

        return f"""Write a weekly coaching review for these trades:

THIS PERIOD'S TRADES:
{trade_lines}
PERIOD STATISTICS:
  Trades taken: {len(trades)}
  Win rate: {summary.get('win_rate', 0):.1f}%
  Total P&L: ${summary.get('total_pnl', 0):+.2f}
  Profit factor: {summary.get('profit_factor', 0):.2f}x
  Expectancy: ${summary.get('expectancy', 0):+.2f} per trade

Focus entirely on behavioral patterns and process quality.
Do not comment on market conditions as explanations for results."""