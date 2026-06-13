import yfinance as yf
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from config.settings import IS_POSTGRES
from core.trade_repository import (
    get_connection,
    _execute,
    _adapt_query,
    _fetch_one,
    IS_POSTGRES,
)

logger = logging.getLogger(__name__)

class MarketDataService:

    def __init__(self):
    
        if not IS_POSTGRES:
            from config.settings import DB_PATH
            from pathlib import Path
            if not Path(DB_PATH).exists():
                raise FileNotFoundError(
                    f"Database not found at {DB_PATH}. "
                    f"Run initialize_database() first."
                )

    def get_snapshot(self, ticker: str) -> Optional[Dict[str, Any]]:

        ticker = ticker.upper().strip()
        today = datetime.now(timezone.utc).date().isoformat()

        cached = self._get_cached_snapshot(ticker, today)
        if cached:
            logger.info(f"Cache hit for {ticker} on {today}")
            return cached
        
        logger.info(f"Cache miss for {ticker} - fetching from Yahoo Finance")
        return self._fetch_and_cache_snapshot(ticker, today)


    def _get_cached_snapshot(
        self,
        ticker: str,
        date: str
    ) -> Optional[Dict[str, Any]]:

        conn = get_connection()
        cursor = _execute(
            conn,
            _adapt_query(
                "SELECT * FROM market_snapshots "
                "WHERE ticker = ? AND snapshot_date = ?"
            ),
            (ticker, date)
        )
        row = _fetch_one(cursor)
        conn.close()
        return row

    def _fetch_and_cache_snapshot(
        self,
        ticker: str,
        date: str
    ) -> Optional[Dict[str, Any]]:

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="2d")

            if hist.empty:
                logger.warning(f"No price history returned for {ticker}")
                return None

            latest = hist.iloc[-1]

            if len(hist) >= 2:
                previous_close = hist.iloc[-2]["Close"]
                current_close = latest["Close"]
                daily_change_pct = ((current_close - previous_close) / previous_close) * 100
            else:
                daily_change_pct = 0.0

            snapshot = {
                "ticker": ticker,
                "snapshot_date": date,
                "open_price": round(float(latest["Open"]), 4),
                "high_price": round(float(latest["High"]), 4),
                "low_price": round(float(latest["Low"]), 4),
                "close_price": round(float(latest["Close"]), 4),
                "volume": float(latest["Volume"]),
                "daily_change_pct": round(daily_change_pct,4),
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }

            self._cache_snapshot(snapshot)

            logger.info(f"Fetched {ticker}: close=${snapshot['close_price']}"
                        f"change={snapshot['daily_change_pct']}%"
                        )
            return snapshot

        except Exception as e:
            logger.error(f"Failed to fetch snapshot for {ticker}: {e}")
            return None

    def _cache_snapshot(self, snapshot: Dict[str, Any]) -> None:

        conn = get_connection()
        params = (
            snapshot["ticker"],
            snapshot["snapshot_date"],
            snapshot["open_price"],
            snapshot["high_price"],
            snapshot["low_price"],
            snapshot["close_price"],
            snapshot["volume"],
            snapshot["daily_change_pct"],
            snapshot["fetched_at"],
        )

        try:
            if IS_POSTGRES:
                sql = """
                    INSERT INTO market_snapshots (
                        ticker, snapshot_date, open_price, high_price,
                        low_price, close_price, volume, daily_change_pct, fetched_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, snapshot_date)
                    DO UPDATE SET
                        open_price       = EXCLUDED.open_price,
                        high_price       = EXCLUDED.high_price,
                        low_price        = EXCLUDED.low_price,
                        close_price      = EXCLUDED.close_price,
                        volume           = EXCLUDED.volume,
                        daily_change_pct = EXCLUDED.daily_change_pct,
                        fetched_at       = EXCLUDED.fetched_at
                """
                _execute(conn, sql, params)
                conn.commit()
            else:
                sql = """
                    INSERT OR REPLACE INTO market_snapshots (
                        ticker, snapshot_date, open_price, high_price,
                        low_price, close_price, volume, daily_change_pct, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                with conn:
                    _execute(conn, sql, params)
        finally:
            conn.close()
        

    def get_price_history(
        self,
        ticker: str,
        period: str = "3mo"
    ) -> Optional[Any]:

        try:
            ticker = ticker.upper().strip()
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)

            if hist.empty:
                logger.warning(f"No history for {ticker} period={period}")
                return None

            logger.info(f"Fetched {len(hist)} days of history for {ticker}")
            return hist

        except Exception as e:
            logger.error(f"Failed to fetch history for {ticker}: {e}")    
            return None

    def get_multiple_snapshot(self, tickers: List[str]) -> Dict[str, Dict]:

        results = {}
        for ticker in tickers:
            snapshot = self.get_snapshot(ticker)
            if snapshot:
                results[ticker.upper()] = snapshot
        return results

    def validate_ticker(self, ticker: str) -> bool:

        try:
            ticker = ticker.upper().strip()
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            is_valid = not hist.empty

            if not is_valid:
                logger.warning(f"Ticker validation failed for: {ticker}")
            return is_valid
        
        except Exception:
            return False