import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from openai import OpenAI
from config.settings import OPENAI_API_KEY
from core.prompt_templates import PromptTemplate

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
        self.templates = PromptTemplate() 

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

    def analyze_single_trade(self, trade: Dict[str, Any], use_few_shot: bool = True,) -> Dict[str, Any]:

        logger.info(
            f"Analyzing trade: {trade.get('ticker')} "
            f"outcome={trade.get('outcome')}"
            f"few_shot={use_few_shot}"
        )

        messages = self.templates.trade_analysis(trade, include_few_shot=use_few_shot)

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
            logger.error(f"JSON parse error: {e}")
            return {
                "success": False,
                "error": f"JSON parse error: {e}",
                "analysis": None,
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
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def detect_behavioral_patterns(
        self,
        ai_context: Dict[str, Any]
    ) -> Dict[str, Any]:

        logger.info("Running behavioral pattern detection")

        messages = self.templates.pattern_detection(ai_context)

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

        messages = self.templates.weekly_summary(weekly_trades, ai_context)

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
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }