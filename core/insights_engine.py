import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

from core.analytics_engine import AnalyticsEngine
from core.ai_engine import AIEngine
from core.trade_repository import (
    TradeRepository,
    get_connection,
    _execute,
    _adapt_query,
    _fetch_rows,
    _fetch_one,
    IS_POSTGRES,
)

logger = logging.getLogger(__name__)

class InsightRepository:

    def _get_connection(self):

        return get_connection()

    def save_insight(
        self,
        insight_type: str,
        content: Dict[str, Any],
        model_used: str,
        prompt_tokens: int,
        completion_tokens: int,
        trade_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> int:

        content_str = json.dumps(content)
        tags_str = ",".join(tags) if tags else None

        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()

        try:
            if IS_POSTGRES:
                sql = _adapt_query("""
                    INSERT INTO ai_insights (
                        user_id, trade_id, insight_type, content,
                        model_used, prompt_tokens, completion_tokens,
                        tags, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
                """)
                cursor = _execute(conn, sql, (
                    user_id, trade_id, insight_type, content_str,
                    model_used, prompt_tokens, completion_tokens,
                    tags_str, now,
                ))
                insight_id = cursor.fetchone()["id"]
                conn.commit()
            else:
                sql = """
                    INSERT INTO ai_insights (
                        user_id, trade_id, insight_type, content,
                        model_used, prompt_tokens, completion_tokens,
                        tags, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                with conn:
                    cursor = _execute(conn, sql, (
                        user_id, trade_id, insight_type, content_str,
                        model_used, prompt_tokens, completion_tokens,
                        tags_str, now,
                    ))
                    insight_id = cursor.lastrowid
        finally:
            conn.close()
        logger.info(
            f"Saved insight id={insight_id} "
            f"type={insight_type} trade_id={trade_id}"
        )
        return insight_id

    def get_insight_by_id(self, insight_id: int) -> Optional[Dict]:

        conn = self._get_connection()
        cursor = _execute(
            conn,
            _adapt_query("SELECT * FROM ai_insights WHERE id = ?"),
            (insight_id,)
        )
        row = _fetch_one(cursor)
        conn.close()

        if not row:
            return None

        return self._deserialize_insight(row)

    def get_insights_for_trade(self, trade_id: int, user_id: str = None) -> List[Dict]:

        conn = self._get_connection()
        if user_id:
            cursor = _execute(
                conn,
                _adapt_query("""
                    SELECT * FROM ai_insights
                    WHERE trade_id = ? AND user_id = ?
                    ORDER BY created_at DESC
                """),
                (trade_id, user_id)
            )
        else:
            cursor = _execute(
                conn,
                _adapt_query("""
                    SELECT * FROM ai_insights
                    WHERE trade_id = ?
                    ORDER BY created_at DESC
                """),
                (trade_id,)
            )

        rows = _fetch_rows(cursor)
        conn.close()

        return [self._deserialize_insight(row) for row in rows]

    def get_insights_by_type(
        self,
        insight_type: str,
        limit: int = 10,
        user_id: str = None
    ) -> List[Dict]:

        conn = self._get_connection()
        if user_id:
            cursor = _execute(
                conn,
                _adapt_query("""
                    SELECT ai.*, t.ticker, t.outcome, t.net_pnl
                    FROM ai_insights ai
                    LEFT JOIN trades t ON ai.trade_id = t.id
                    WHERE ai.insight_type = ? AND ai.user_id = ?
                    ORDER BY ai.created_at DESC
                    LIMIT ?
                """),
                (insight_type, user_id, limit)
            )
        else:
            cursor = _execute(
                conn,
                _adapt_query("""
                    SELECT ai.*, t.ticker, t.outcome, t.net_pnl
                    FROM ai_insights ai
                    LEFT JOIN trades t ON ai.trade_id = t.id
                    WHERE ai.insight_type = ?
                    ORDER BY ai.created_at DESC
                    LIMIT ?
                """),
                (insight_type, limit)
            )

        rows = _fetch_rows(cursor)
        conn.close()

        return [self._deserialize_insight(row) for row in rows]

    def get_all_insights(self, limit: int = 50, user_id: str = None) -> List[Dict]:
    
        conn = self._get_connection()
        if user_id:
            cursor = _execute(
                conn,
                _adapt_query("""
                    SELECT ai.*, t.ticker, t.outcome, t.net_pnl
                    FROM ai_insights ai
                    LEFT JOIN trades t ON ai.trade_id = t.id
                    WHERE ai.user_id = ?
                    ORDER BY ai.created_at DESC
                    LIMIT ?
                """),
                (user_id, limit)
            )
        else:
            cursor = _execute(
                conn,
                _adapt_query("""
                    SELECT ai.*, t.ticker, t.outcome, t.net_pnl
                    FROM ai_insights ai
                    LEFT JOIN trades t ON ai.trade_id = t.id
                    ORDER BY ai.created_at DESC
                    LIMIT ?
                """),
                (limit,)
            )

        rows = _fetch_rows(cursor)
        conn.close()

        return [self._deserialize_insight(row) for row in rows]

    def get_insight_count_by_type(self, user_id: str = None) -> Dict[str, int]:
        
        conn = self._get_connection()
        if user_id:
            cursor = _execute(
                conn,
                _adapt_query("""
                    SELECT insight_type, COUNT(*) as count
                    FROM ai_insights
                    WHERE user_id = ?
                    GROUP BY insight_type
                """),
                (user_id,)
            )
        else:
            cursor = _execute(
                conn,
                """
                    SELECT insight_type, COUNT(*) as count
                    FROM ai_insights
                    GROUP BY insight_type
                """
            )

        rows = _fetch_rows(cursor)
        conn.close()

        return {row["insight_type"]: row["count"] for row in rows}

    def get_total_tokens_used(self) -> Dict[str, int]:
        
        conn = self._get_connection()
        cursor = _execute(conn, """
            SELECT
                SUM(prompt_tokens) as total_prompt,
                SUM(completion_tokens) as total_completion,
                SUM(prompt_tokens + completion_tokens) as total_all
            FROM ai_insights
        """)
        row = _fetch_one(cursor)
        conn.close()

        if not row or row["total_all"] is None:
            return {
                "total_prompt": 0,
                "total_completion": 0,
                "total_all": 0,
                "estimated_cost_usd": 0.0,
            }

        total_prompt = row["total_prompt"] or 0
        total_completion = row["total_completion"] or 0
        total_all = row["total_all"] or 0

        estimated_cost = (
            (total_prompt / 1000 * 0.005) +
            (total_completion / 1000 * 0.015)
        )

        return {
            "total_prompt": total_prompt,
            "total_completion": total_completion,
            "total_all": total_all,
            "estimated_cost_usd": round(estimated_cost, 4),
        }

    def delete_insight(self, insight_id: int) -> bool:

        conn = self._get_connection()
        try:
            cursor = _execute(
                conn,
                _adapt_query("DELETE FROM ai_insights WHERE id = ?"),
                (insight_id,)
            )
            deleted = cursor.rowcount > 0
            conn.commit()
        finally:
            conn.close()
        return deleted

    def _deserialize_insight(self, row: Dict) -> Dict:

        if "content" in row and isinstance(row["content"], str):
            try:
                row["content"] = json.loads(row["content"])
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse insight content as JSON "
                    f"for insight id={row.get('id')}"
                )
        
        if "tags" in row and isinstance(row["tags"], str):
            row["tags"] = row["tags"].split(",") if row["tags"] else []

        return row

class InsightsEngine:

    def __init__(self):

        self.trade_repo = TradeRepository()
        self.analytics = AnalyticsEngine()
        self.insight_repo = InsightRepository()

        try:
            self.ai = AIEngine()
            self.ai_available = True
        except EnvironmentError:
            self.ai = None
            self.ai_available = False
            logger.warning(
                "AIEngine unavailable — OPENAI_API_KEY not set. "
                "Insights generation disabled."
            )

    def analyze_and_store_trade(
        self,
        trade_id: int,
        user_id: str = None
    ) -> Dict[str, Any]:

        if not self.ai_available:
            return {
                "success": False,
                "error": "AI Engine not available — check OPENAI_API_KEY",
            }

        trade = self.trade_repo.get_trade_by_id(trade_id, user_id=user_id)

        if not trade:
            return {
                "success": False,
                "error": f"Trade id={trade_id} not found",
            }

        if trade.get("outcome") == "open":
            return {
                "success": False,
                "error": "Cannot analyze an open trade — close it first",
            }

        logger.info(f"Analyzing trade id={trade_id} ticker={trade['ticker']}")

        ai_result = self.ai.analyze_single_trade(trade)

        if not ai_result["success"]:
            return {
                "success": False,
                "error": ai_result["error"],
            }

        tags = self._extract_tags_from_analysis(
            ai_result["analysis"],
            trade
        )

        insight_id = self.insight_repo.save_insight(
            insight_type="trade_analysis",
            content=ai_result["analysis"],
            model_used=ai_result["model"],
            prompt_tokens=ai_result["prompt_tokens"],
            completion_tokens=ai_result["completion_tokens"],
            trade_id=trade_id,
            tags=tags,
            user_id=user_id,
        )

        return {
            "success": True,
            "insight_id": insight_id,
            "trade_id": trade_id,
            "ticker": trade["ticker"],
            "analysis": ai_result["analysis"],
            "total_tokens": ai_result["total_tokens"],
            "model": ai_result["model"],
            "generated_at": ai_result["generated_at"],
        }

    def detect_and_store_patterns(self, user_id: str = None) -> Dict[str, Any]:

        if not self.ai_available:
            return {
                "success": False,
                "error": "AI Engine not available — check OPENAI_API_KEY",
            }

        df = self.trade_repo.get_trades_as_dataframe(user_id=user_id)

        if df.empty or len(df) < 3:
            return {
                "success": False,
                "error": (
                    "Need at least 3 closed trades for pattern detection. "
                    f"Currently have {len(df)}."
                ),
            }

        logger.info(
            f"Running pattern detection on {len(df)} trades"
        )

        ai_context = self.analytics.build_ai_context(df)
        ai_result = self.ai.detect_behavioral_patterns(ai_context)

        if not ai_result["success"]:
            return {
                "success": False,
                "error": ai_result["error"],
            }

        insight_id = self.insight_repo.save_insight(
            insight_type="pattern_detection",
            content=ai_result["patterns"],
            model_used=ai_result["model"],
            prompt_tokens=ai_result["prompt_tokens"],
            completion_tokens=ai_result["completion_tokens"],
            trade_id=None,
            tags=["patterns", "behavioral", "portfolio"],
            user_id=user_id,
        )

        return {
            "success": True,
            "insight_id": insight_id,
            "patterns": ai_result["patterns"],
            "trades_analyzed": len(df),
            "total_tokens": ai_result["total_tokens"],
            "model": ai_result["model"],
            "generated_at": ai_result["generated_at"],
        }

    def generate_and_store_weekly_summary(
        self,
        days_back: int = 7,
        user_id: str = None
    ) -> Dict[str, Any]:

        if not self.ai_available:
            return {
                "success": False,
                "error": "AI Engine not available — check OPENAI_API_KEY",
            }

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        all_trades = self.trade_repo.get_all_trades(closed_only=True, user_id=user_id)

        def _make_aware(date_str: str) -> datetime:
    
            dt = datetime.fromisoformat(date_str.split("+")[0])
            return dt.replace(tzinfo=timezone.utc)

        weekly_trades = [
            t for t in all_trades
            if _make_aware(t["entry_date"]) >= cutoff
]

        if not weekly_trades:
            return {
                "success": False,
                "error": (
                    f"No closed trades in the past {days_back} days. "
                    "Log some trades first."
                ),
            }

        logger.info(
            f"Generating weekly summary for "
            f"{len(weekly_trades)} trades"
        )

        df = self.trade_repo.get_trades_as_dataframe(user_id=user_id)
        ai_context = self.analytics.build_ai_context(df)

        ai_result = self.ai.generate_weekly_summary(
            weekly_trades, ai_context
        )

        if not ai_result["success"]:
            return {
                "success": False,
                "error": ai_result["error"],
            }

        insight_id = self.insight_repo.save_insight(
            insight_type="weekly_summary",
            content=ai_result["summary"],
            model_used=ai_result["model"],
            prompt_tokens=ai_result["prompt_tokens"],
            completion_tokens=ai_result["completion_tokens"],
            trade_id=None,
            tags=["weekly", "summary", "coaching"],
            user_id=user_id,
        )

        return {
            "success": True,
            "insight_id": insight_id,
            "summary": ai_result["summary"],
            "trade_count": len(weekly_trades),
            "total_tokens": ai_result["total_tokens"],
            "model": ai_result["model"],
            "generated_at": ai_result["generated_at"],
        }

    def get_trade_insight_history(
        self,
        trade_id: int,
        user_id: str = None
    ) -> List[Dict]:

        return self.insight_repo.get_insights_for_trade(trade_id, user_id=user_id)

    def get_pattern_history(
        self,
        limit: int = 5,
        user_id: str = None
    ) -> List[Dict]:

        return self.insight_repo.get_insights_by_type(
            "pattern_detection", limit=limit, user_id=user_id
        )

    def get_weekly_summary_history(
        self,
        limit: int = 5,
        user_id: str = None
    ) -> List[Dict]:

        return self.insight_repo.get_insights_by_type(
            "weekly_summary", limit=limit, user_id=user_id
        )
    
    def get_all_insights(self, limit: int = 50, user_id: str = None) -> List[Dict]:

        return self.insight_repo.get_all_insights(limit=limit, user_id=user_id)

    def get_usage_stats(self, user_id: str = None) -> Dict[str, Any]:

        token_stats = self.insight_repo.get_total_tokens_used()
        insight_counts = self.insight_repo.get_insight_count_by_type(user_id=user_id)

        return {
            "total_insights": sum(insight_counts.values()),
            "by_type": insight_counts,
            "token_usage": token_stats,
        }

    def _extract_tags_from_analysis(
        self,
        analysis: Dict,
        trade: Dict,
    ) -> List[str]:

        tags = []

        outcome = trade.get("outcome", "")
        if outcome:
            tags.append(outcome)

        strategy = trade.get("strategy_name", "")
        if strategy:
            tags.append(strategy.lower().replace(" ", "_"))

        emotion = trade.get("emotional_state", "")
        if emotion:
            tags.append(emotion)

        severity = analysis.get("severity", "")
        if severity:
            tags.append(severity)

        if trade.get("fomo_factor"):
            tags.append("fomo")
        if not trade.get("followed_plan"):
            tags.append("unplanned")

        return tags