import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
MAX_TOKENS_ANALYSIS = 1000      # Single trade analysis
MAX_TOKENS_PATTERNS = 1500      # Pattern detection across many trades
MAX_TOKENS_SUMMARY = 1200       # Weekly summary narrative

class AIEngine:

    def __init__(self):

        if not OPENAI_API_KEY:
            raise EnvironmentError(
                "OPENAI_API_KEY not found in environment. "
                "Add it to your .env file."
            ) 

        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = DEFAULT_MODEL

        logger.info(f"AIEngine initialized with model: {self.model}")

    def _call_api(
        self,
        messages: List[Dict],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        json_mode: bool = False,
        retries: int = 2,
    ) -> Dict[str, Any]:

        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            params["response_format"] = {"type": "json_object"}

        for attempt in range(retries + 1):

            try:
                response = self.client.chat.completions.create(**params)
                content = response.choices[0].message.content

                usage = response.usage
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
                total_tokens = usage.total_tokens

                logger.info(
                    f"API call successful — "
                    f"prompt: {prompt_tokens} tokens, "
                    f"completion: {completion_tokens} tokens, "
                    f"total: {total_tokens} tokens"
                )

                return {
                    "success": True,
                    "content": content,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "model": self.model,
                    "error": None,
                }
            
            except Exception as e:
                logger.warning(
                    f"API call attempt {attempt + 1} failed: {e}"
                )

                if retries < 2:

                    wait_time = 2 ** (attempt + 1)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

                else:
                    return {
                        "success": False,
                        "content": None,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "model": self.model,
                        "error": str(e),
                    }

    def _build_trade_analysis_prompt(self, trade: Dict[str, Any]) -> List[Dict]:

        system_prompt = """You are a professional trading coach and behavioral finance analyst with 20 years of experience. You specialize in identifying psychological patterns that cause traders to make repeated mistakes.

Your analysis is:
- Direct and specific — never generic
- Data-driven — always reference the specific numbers provided
- Constructive — identify problems AND provide actionable solutions
- Behavioral — focus on psychology, not just technical trade mechanics

You must respond with a JSON object containing exactly these keys:
{
    "trade_quality_score": <integer 1-10, overall trade quality>,
    "primary_mistake": <string, the single most important error if any, or "None" if no mistakes>,
    "psychological_pattern": <string, the behavioral pattern this trade represents>,
    "risk_management_assessment": <string, assessment of stop loss and R:R discipline>,
    "what_went_well": <string, specific positives in this trade>,
    "what_went_wrong": <string, specific negatives, "None" if none>,
    "root_cause": <string, the underlying reason for any mistakes>,
    "specific_suggestions": <list of 2-3 specific, actionable improvements>,
    "severity": <"positive"|"minor_issue"|"significant_issue"|"critical_issue">
}

Only output the JSON object. No preamble. No explanation outside the JSON."""

        pnl_str = f"${trade.get('gross_pnl', 0):+.2f}" if trade.get('gross_pnl') is not None else "Unknown"
        return_str = f"{trade.get('return_pct', 0):+.2f}%" if trade.get('return_pct') is not None else "Unknown"

        # Build planned R:R string
        planned_rr = "Not set"
        if trade.get('planned_risk_per_share') and trade.get('planned_reward_per_share'):
            risk = trade['planned_risk_per_share']
            reward = trade['planned_reward_per_share']
            if risk > 0:
                planned_rr = f"{reward/risk:.2f}:1"

        user_prompt = f"""Analyze this trade and identify behavioral patterns:

TRADE DETAILS:
  Ticker: {trade.get('ticker', 'Unknown')}
  Direction: {trade.get('direction', 'long').upper()}
  Quantity: {trade.get('quantity', 0)} shares
  Entry Price: ${trade.get('entry_price', 0):.2f}
  Exit Price: ${trade.get('exit_price', 0):.2f} if trade.get('exit_price') else 'Still open'
  Outcome: {trade.get('outcome', 'Unknown').upper()}
  Gross P&L: {pnl_str}
  Return: {return_str}

RISK MANAGEMENT:
  Stop Loss: ${trade.get('stop_loss_price', 0):.2f} if trade.get('stop_loss_price') else 'Not set'
  Take Profit: ${trade.get('take_profit_price', 0):.2f} if trade.get('take_profit_price') else 'Not set'
  Planned R:R: {planned_rr}
  Actual R:R: {f"{trade.get('actual_rr_ratio', 0):.2f}:1" if trade.get('actual_rr_ratio') else 'Unknown'}
  Stop Loss Honored: {bool(trade.get('stop_loss_honored', True))}
  Exit Reason: {trade.get('exit_reason', 'Unknown')}

PSYCHOLOGY:
  Emotional State: {trade.get('emotional_state', 'Unknown')}
  Confidence Level: {trade.get('confidence_level', 'Unknown')}/10
  FOMO Trade: {bool(trade.get('fomo_factor', False))}
  Followed Plan: {bool(trade.get('followed_plan', True))}

STRATEGY & CONTEXT:
  Strategy: {trade.get('strategy_name', 'Not specified')}
  Timeframe: {trade.get('timeframe', 'Not specified')}
  Market Condition: {trade.get('market_condition', 'Unknown')}
  SPY Direction: {trade.get('spy_direction', 'Unknown')}

TRADER'S REASONING:
  Entry Reasoning: "{trade.get('entry_reasoning', 'Not provided')}"
  Exit Reasoning: "{trade.get('exit_reasoning', 'Not provided')}"

Analyze this trade for psychological patterns, risk management quality, 
and behavioral issues. Be specific — reference the actual numbers above."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def analyze_single_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:

        logger.info(
            f"Analyzing trade: {trade.get('ticker')} "
            f"outcome={trade.get('outcome')}"
        )

        messages = self._build_trade_analysis_prompt(trade)

        result = self._call_api(
            messages=messages,
            max_tokens=MAX_TOKENS_ANALYSIS,
            temperature=0.3,        # Low temperature — consistent analysis
            json_mode=True,         # Force structured JSON output
        )

        if not result["success"]:
            return {
                "success": False,
                "error": result["error"],
                "analysis": None,
                "trade_id": trade.get("id"),
                "ticker": trade.get("ticker"),
            }

        # Parse the JSON response
        try:
            analysis = json.loads(result["content"])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "analysis": None,
                "trade_id": trade.get("id"),
                "ticker": trade.get("ticker"),
            }

        return {
            "success": True,
            "analysis": analysis,
            "trade_id": trade.get("id"),
            "ticker": trade.get("ticker"),
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
            "model": result["model"],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _build_pattern_detection_prompt(self, ai_context: Dict[str, Any]) -> List[Dict]:

        system_prompt = """You are a quantitative behavioral finance analyst specializing in retail trader psychology. You analyze statistical patterns in trading data to identify systematic behavioral biases and their financial impact.

Your analysis must be:
- Evidence-based: every claim references specific statistics provided
- Prioritized: rank patterns by financial impact (most costly first)  
- Actionable: every pattern comes with a specific corrective behavior
- Honest: do not soften findings to spare feelings

You must respond with a JSON object containing exactly these keys:
{
    "overall_assessment": <string, 2-3 sentence summary of the trader's profile>,
    "performance_grade": <"A"|"B"|"C"|"D"|"F">,
    "critical_patterns": [
        {
            "pattern_name": <string>,
            "evidence": <string, specific statistics that prove this pattern>,
            "financial_impact": <string, estimated cost of this pattern>,
            "correction": <string, specific behavioral change to make>
        }
    ],
    "strengths": [<string>, <string>],
    "top_priority_action": <string, the single most important thing to change>,
    "estimated_improvement": <string, projected win rate or P&L improvement if top action is taken>
}

Only output the JSON object. No text outside the JSON."""

        summary = ai_context.get("summary", {})
        emotion_wr = ai_context.get("emotion_win_rates", {})
        strategy_wr = ai_context.get("strategy_win_rates", {})
        fomo = ai_context.get("fomo_impact", {})
        plan = ai_context.get("plan_adherence", {})
        rr = ai_context.get("rr_analysis", {})
        risk = ai_context.get("risk_metrics", {})
        behavioral = ai_context.get("behavioral_correlations", {})
        confidence = ai_context.get("avg_confidence_by_outcome", {})

        emotion_table = ""
        for emotion, stats in emotion_wr.items():
            emotion_table += (
                f"  {emotion}: {stats['win_rate']}% win rate "
                f"({stats['total_trades']} trades, "
                f"avg P&L ${stats['avg_pnl']:+.2f})\n"
            )

        strategy_table = ""
        for strategy, stats in strategy_wr.items():
            strategy_table += (
                f"  {strategy}: {stats['win_rate']}% win rate "
                f"({stats['total_trades']} trades, "
                f"avg P&L ${stats['avg_pnl']:+.2f})\n"
            )

        user_prompt = f"""Analyze these trading statistics for behavioral patterns:

OVERALL PERFORMANCE:
  Total Trades: {summary.get('total_trades', 0)}
  Win Rate: {summary.get('win_rate', 0):.1f}%
  Total P&L: ${summary.get('total_pnl', 0):+,.2f}
  Avg Trade P&L: ${summary.get('avg_trade_pnl', 0):+,.2f}
  Profit Factor: {summary.get('profit_factor', 0):.2f}x
  Expectancy: ${summary.get('expectancy', 0):+,.2f} per trade

RISK METRICS:
  Sharpe Ratio: {risk.get('sharpe_ratio', 0):.2f} ({risk.get('sharpe_interpretation', 'N/A')})
  Max Drawdown: {risk.get('max_drawdown_pct', 0):.2f}%
  Return Volatility: {risk.get('return_volatility', 0):.2f}%

PERFORMANCE BY EMOTIONAL STATE:
{emotion_table if emotion_table else "  No emotional state data"}

PERFORMANCE BY STRATEGY:
{strategy_table if strategy_table else "  No strategy data"}

FOMO ANALYSIS:
  FOMO trade win rate: {fomo.get('fomo_win_rate', 0):.1f}% ({fomo.get('fomo_trade_count', 0)} trades)
  Planned trade win rate: {fomo.get('non_fomo_win_rate', 0):.1f}% ({fomo.get('non_fomo_trade_count', 0)} trades)
  Cost of FOMO per trade: ${fomo.get('fomo_cost', 0):+,.2f}

PLAN ADHERENCE:
  Trades with plan: {plan.get('planned_trade_count', 0)} trades, {plan.get('planned_win_rate', 0):.1f}% win rate
  Trades without plan: {plan.get('unplanned_trade_count', 0)} trades, {plan.get('unplanned_win_rate', 0):.1f}% win rate

RISK:REWARD DISCIPLINE:
  Avg planned R:R: {rr.get('avg_planned_rr', 0):.2f}:1
  Avg actual R:R: {rr.get('avg_actual_rr', 0):.2f}:1
  R:R adherence rate: {rr.get('rr_adherence_rate', 0):.1f}%
  Cutting winners early: {rr.get('cutting_winners_early', False)}

CONFIDENCE CALIBRATION:
  Avg confidence on wins: {confidence.get('avg_confidence_wins', 0):.1f}/10
  Avg confidence on losses: {confidence.get('avg_confidence_losses', 0):.1f}/10

MOST PREDICTIVE BEHAVIORAL FACTOR:
  {behavioral.get('most_predictive_feature', 'N/A')} 
  (correlation with returns: {behavioral.get('top_correlation', 0):+.3f})

Identify the critical behavioral patterns, rank them by financial impact,
and provide specific actionable corrections for each."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def detect_behavioral_patterns(
        self,
        ai_context: Dict[str, Any]
    ) -> Dict[str, Any]:

        logger.info("Running behavioral pattern detection")

        messages = self._build_pattern_detection_prompt(ai_context)

        result = self._call_api(
            messages=messages,
            max_tokens=MAX_TOKENS_PATTERNS,
            temperature=0.3,
            json_mode=True,
        )

        if not result["success"]:
            return {
                "success": False,
                "error": result["error"],
                "patterns": None,
            }

        try:
            patterns = json.loads(result["content"])
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "patterns": None,
            }

        return {
            "success": True,
            "patterns": patterns,
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
            "model": result["model"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_weekly_summary_prompt(
        self,
        weekly_trades: List[Dict],
        ai_context: Dict[str, Any]
    ) -> List[Dict]:

        system_prompt = """You are a trading coach writing a weekly performance review for a trader. Your tone is professional, direct, and encouraging without being dishonest. You focus on behavioral patterns, not market conditions.

Write in second person ("You entered...", "Your win rate...").
Be specific about what happened this week. Reference actual trades.
End with one clear focus for the coming week.

Respond with a JSON object:
{
    "week_grade": <"A"|"B"|"C"|"D"|"F">,
    "headline": <string, one sentence capturing the week>,
    "performance_narrative": <string, 3-4 sentences about this week's results>,
    "best_moment": <string, the best trade or decision this week>,
    "learning_moment": <string, the most important lesson from a mistake>,
    "emotional_pattern": <string, observation about emotional state this week>,
    "focus_for_next_week": <string, one specific behavioral target>
}"""

        trades_text = ""
        for i, trade in enumerate(weekly_trades[:10], 1):
            outcome_emoji = "✅" if trade.get("outcome") == "win" else "❌"
            trades_text += (
                f"{i}. {outcome_emoji} {trade.get('ticker')} "
                f"{trade.get('direction', 'long').upper()} — "
                f"P&L: ${trade.get('net_pnl', 0):+.2f} | "
                f"Emotion: {trade.get('emotional_state', 'unknown')} | "
                f"FOMO: {bool(trade.get('fomo_factor', False))} | "
                f"Followed plan: {bool(trade.get('followed_plan', True))}\n"
            )

        summary = ai_context.get("summary", {})

        user_prompt = f"""Write a weekly trading review for these trades:

THIS WEEK'S TRADES:
{trades_text}

WEEK STATISTICS:
  Trades taken: {len(weekly_trades)}
  Win rate: {summary.get('win_rate', 0):.1f}%
  Total P&L: ${summary.get('total_pnl', 0):+.2f}
  Profit factor: {summary.get('profit_factor', 0):.2f}x

Write a behavioral coaching review focused on patterns in psychology, discipline, and decision-making — not market conditions."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def generate_weekly_summary(
        self,
        weekly_trades: List[Dict],
        ai_context: Dict[str, Any]
    ) -> Dict[str, Any]:

        if not weekly_trades:
            return {
                "success": False,
                "error": "No trades this week to summarize",
                "summary": None,
            }

        logger.info(
            f"Generating weekly summary for {len(weekly_trades)} trades"
        )

        messages = self._build_weekly_summary_prompt(
            weekly_trades, ai_context
        )

        result = self._call_api(
            messages=messages,
            max_tokens=MAX_TOKENS_SUMMARY,
            temperature=0.7,    # Higher — more natural narrative language
            json_mode=True,
        )

        if not result["success"]:
            return {
                "success": False,
                "error": result["error"],
                "summary": None,
            }

        try:
            summary = json.loads(result["content"])
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "summary": None,
            }

        return {
            "success": True,
            "summary": summary,
            "trade_count": len(weekly_trades),
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
            "model": result["model"],
            "generated_at": datetime.utcnow().isoformat(),
        }