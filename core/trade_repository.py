import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from config.settings import DB_PATH

from sqlalchemy import(
    create_engine,
    Column,
    Integer,
    Float,
    String,
    Boolean,
    DateTime,
    Text,
    Index
)
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import event

Base = declarative_base()

#Logging setup
logger = logging.getLogger(__name__)

class TradeModel(Base):

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- TIMESTAMPS ---
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    # --- WHAT WAS TRADED ---
    ticker = Column(String, nullable=False, index=True)
    company_name = Column(String)
    sector = Column(String)

    # --- POSITION ---
    quantity = Column(Float, nullable=False)
    direction = Column(String, default="long")
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    entry_date = Column(String, nullable=False, index=True)
    exit_date = Column(String)

    # --- RISK MANAGEMENT ---
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    planned_risk_per_share = Column(Float)
    planned_reward_per_share = Column(Float)

    # --- OUTCOMES ---
    gross_pnl = Column(Float)
    net_pnl = Column(Float)
    return_pct = Column(Float)
    actual_rr_ratio = Column(Float)
    outcome = Column(String, index=True)

    # --- EXIT BEHAVIOUR ---
    exit_reason = Column(String)
    stop_loss_honored = Column(Integer)

    # --- STRATEGY ---
    strategy_name = Column(String)
    timeframe = Column(String)
    setup_description = Column(Text)

    # --- REASONING ---
    entry_reasoning = Column(Text)
    exit_reasoning = Column(Text)

    # --- PSYCHOLOGY ---
    emotional_state = Column(String, index=True)
    confidence_level = Column(Integer)
    fomo_factor = Column(Integer, default=0)
    followed_plan = Column(Integer, default=1)
    pre_trade_notes = Column(Text)

    # --- MARKET CONTEXT ---
    market_condition = Column(String)
    spy_direction = Column(String)
    sector_performance = Column(Float)

    # --- COSTS ---
    comission = Column(Float, default=0.0)

    def to_dict(self) -> Dict[str, Any]:

        return{
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:

        return(
            f"<Trade id={self.id} ticker={self.ticker} "
            f"outcome={self.outcome} pnl={self.net_pnl}>"
        )

def get_engine():

    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
        echo=False
    )

    return engine

#Database Initialization
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn

def initialize_database() -> None:
    logger.info(f"Initializing database at {DB_PATH}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection()

    with conn:
        # --- Trades Table ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades(
                -- IDENTITY
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL,
                
                -- WHAT WAS TRADED
                ticker                  TEXT NOT NULL,
                company_name            TEXT,
                sector                  TEXT,
                
                -- POSITION DETAILS
                quantity                REAL NOT NULL CHECK(quantity>0),

                direction               TEXT NOT NULL DEFAULT 'long'
                                        CHECK(direction IN ('long', 'short')),

                entry_price             REAL NOT NULL CHECK(entry_price>0),
                exit_price              REAL CHECK(exit_price>0),

                entry_date              TEXT NOT NULL,
                exit_date               TEXT,

                -- RISK MANAGEMENT
                stop_loss_price         REAL,
                take_profit_price       REAL,

                planned_risk_per_share    REAL,
                planned_reward_per_share  REAL,

                -- CALCULATED_OUTCOMES
                gross_pnl               REAL,
                net_pnl                 REAL,
                return_pct              REAL,
                actual_rr_ratio         REAL,

                outcome                 TEXT CHECK(
                                            outcome IN (
                                                'win', 
                                                'loss', 
                                                'breakeven', 
                                                'open'
                                            )
                                        ),

                -- EXIT BEHAVIOUR
                exit_reason             TEXT CHECK(
                                            exit_reason IN (
                                                'stop_loss_hit', 
                                                'take_profit_hit', 
                                                'manual', 
                                                'time',
                                                 NULL
                                            )
                                        ),

                stop_loss_honored       INTEGER DEFAULT NULL
                                        CHECK(
                                            stop_loss_honored IN (0, 1, NULL)
                                        ),

                -- STRATEGY
                strategy_name           TEXT,
                timeframe               TEXT CHECK(
                                            timeframe IN (
                                                'scalp', 
                                                'intraday', 
                                                'swing', 
                                                'position', 
                                                NULL
                                            )
                                        ),

                setup_description       TEXT,

                --- REASONING (fed to AI)
                entry_reasoning         TEXT,
                exit_reasoning          TEXT,

                -- PSYCHOLOGY
                emotional_state         TEXT CHECK(
                                            emotional_state IN (
                                                    'calm', 
                                                    'anxious', 
                                                    'excited', 
                                                    'fearful', 
                                                    'confident', 
                                                    'revenge', 
                                                    'neutral', 
                                                    NULL
                                            )
                                        ),

                confidence_level        INTEGER CHECK(
                                            confidence_level BETWEEN 1 AND 10 
                                            OR confidence_level is NULL
                                        ),

                fomo_factor             INTEGER DEFAULT 0
                                        CHECK (fomo_factor IN (0,1)),

                followed_plan           INTEGER DEFAULT 1
                                        CHECK (followed_plan IN (0,1)),
                                
                -- MARKET CONTEXT
                market_condition        TEXT CHECK(
                                            market_condition IN (
                                                'trending_up', 
                                                'trending_down',
                                                'ranging', 
                                                'volatile', 
                                                NULL
                                            )
                                        ),

                spy_direction           TEXT CHECK(
                                            spy_direction IN (
                                                'up', 
                                                'down', 
                                                'flat', 
                                                NULL
                                            )
                                        ),

                sector_performance      REAL,

                -- COSTS
                comission               REAL DEFAULT 0.0
            )
        """)

        # --- AI Insights Table ---
        conn.execute("""

            CREATE TABLE IF NOT EXISTS ai_insights (

                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id                INTEGER REFERENCES trades(id) ON DELETE CASCADE,
                insight_type            TEXT NOT NULL 
                                        CHECK(
                                            insight_type IN (
                                                'trade_analysis',
                                                'pattern_detection',
                                                'weekly_summary',
                                                'coaching'
                                            )
                                        ),

                content                 TEXT NOT NULL,
                model_used              TEXT NOT NULL,
                prompt_tokens           INTEGER,
                completion_tokens       INTEGER,
                tags                    TEXT,
                created_at              TEXT NOT NULL
            )
        """)

        # --- Market Snapshots Table ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker                  TEXT NOT NULL,
                snapshot_date           TEXT NOT NULL,
                open_price              REAL,
                high_price              REAL,
                low_price               REAL,
                close_price             REAL,
                volume                  REAL,
                daily_change_pct        REAL,
                fetched_at              TEXT NOT NULL,

                -- Prevent Duplicate snapshots for same ticker + date
                UNIQUE(ticker, snapshot_date)            
            )
        """)

        # --- Indexes ---
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_ticker
            ON trades(ticker)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_entry_date
            ON trades(entry_date)      
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_outcome
            ON trades(outcome)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_emotional_state
            ON trades(emotional_state) 
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_insights_trade_id
            ON ai_insights(trade_id)
        """)

        # conn.close()
        logger.info("Database initialization complete")

# --- Helper Function ---
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _calculate_trade_metrics(
    entry_price: float,
    exit_price: float,
    quantity: float,
    commission: float = 0.0,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None
) -> Dict[str, Any]:

    gross_pnl = (exit_price - entry_price) * quantity
    net_pnl = gross_pnl - commission

    capital_deployed = entry_price * quantity
    return_pct = (gross_pnl / capital_deployed) * 100 if capital_deployed > 0 else 0.0

    if net_pnl > 0.01:
        outcome = "win"
    elif net_pnl < -0.01:
        outcome = "loss"
    else:
        outcome = "breakeven"

    actual_rr = None
    if stop_loss_price is not None:
        actual_risk_per_share = abs(entry_price - stop_loss_price)
        actual_reward_per_share = abs(exit_price - entry_price)
        if actual_risk_per_share > 0:
            actual_rr = round(actual_reward_per_share / actual_risk_per_share, 2)

    return {
        "gross_pnl": round(gross_pnl, 2),
        "net_pnl": round(net_pnl, 2),
        "return_pct": round(return_pct, 2),
        "outcome": outcome,
        "actual_rr_ratio": actual_rr
    }

class TradeRepository:

    def insert_trade(self, trade_data: Dict[str, Any]) -> int:

        now = _now()

        if trade_data.get("exit_price") and trade_data.get("entry_price"):
            metrics = _calculate_trade_metrics(
                entry_price=trade_data["entry_price"],
                exit_price=trade_data["exit_price"],
                quantity=trade_data["quantity"],
                commission=trade_data.get("commission", 0.0),
                stop_loss_price=trade_data.get("stop_loss_price"),
                take_profit_price=trade_data.get("take_profit_price")
            )
            trade_data.update(metrics)
        else:
            trade_data["outcome"] = "open"

        if trade_data.get("stop_loss_price") and trade_data.get("take_profit_price"):
            trade_data["planned_risk_per_share"] = round(abs(trade_data["entry_price"]-trade_data["stop_loss_price"]), 4)
        
        if trade_data.get("take_profit_price") and trade_data.get("entry_price"):
            trade_data["planned_reward_per_share"] = round(abs(trade_data["take_profit_price"]-trade_data["entry_price"]), 4)

        trade_data["created_at"] = now
        trade_data["updated_at"] = now

        columns = ", ".join(trade_data.keys())
        placeholders = ", ".join(["?" for _ in trade_data])
        sql = f"INSERT INTO trades ({columns}) VALUES ({placeholders})"

        conn = get_connection()
        with conn:
            cursor = conn.execute(sql, list(trade_data.values()))
            trade_id = cursor.lastrowid
        conn.close()
        logger.info(f"Inserted Trade id={trade_id} ticker={trade_data.get('ticker')}")
        return trade_id

    def get_all_trades(self, closed_only: bool = False) -> List[Dict]:

        conn = get_connection()

        if closed_only:
            sql = """ 
                SELECT * FROM trades 
                WHERE outcome != 'open'
                ORDER BY entry_date DESC
            """
        else:
            sql = "SELECT * FROM trades ORDER BY entry_date DESC"
        
        cursor = conn.execute(sql)

        trades = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return trades

    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:

        conn = get_connection()
        cursor = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        exit_date: str,
        exit_reason: str,
        exit_reasoning: Optional[str] = None,
        stop_loss_honored: Optional[bool] = None
    ) -> bool:

        existing = self.get_trade_by_id(trade_id)

        if not existing:
            logger.warning(f"Attempted to close non-existent trade id={trade_id}")
            return False

        if existing["outcome"] != "open":
            logger.warning(f"Attempted to close already closed trade id={trade_id}")
            return False

        metrics = _calculate_trade_metrics(
            entry_price=existing["entry_price"],
            exit_price=exit_price,
            quantity=existing["quantity"],
            commission=existing.get("commission", 0.0),
            stop_loss_price=existing.get("stop_loss_price")
        )

        conn = get_connection()
        with conn:
            conn.execute("""
                UPDATE trades SET
                    exit_price          = ?,
                    exit_date           = ?,
                    exit_reason         = ?, 
                    exit_reasoning      = ?,
                    stop_loss_honored   = ?,
                    gross_pnl           = ?,
                    net_pnl             = ?,
                    return_pct          = ?,
                    outcome             = ?,
                    actual_rr_ratio     = ?,
                    updated_at          = ?
                WHERE id = ?
            """, (
                exit_price,
                exit_date,
                exit_reason,
                exit_reasoning,
                int(stop_loss_honored) if stop_loss_honored is not None else None,
                metrics["gross_pnl"],
                metrics["net_pnl"],
                metrics["return_pct"],
                metrics["outcome"],
                metrics["actual_rr_ratio"],
                _now(),
                trade_id
            ))

        conn.close()
        logger.info(f"Closed trade id={trade_id} outcome={metrics['outcome']}"
                    f"pnl={metrics['net_pnl']}")

        return True

    def get_trades_by_ticker(self, ticker: str) -> List[Dict]:

        conn = get_connection()
        cursor = conn.execute("SELECT * FROM trades WHERE ticker = ? ORDER BY entry_date DESC", (ticker.upper(),))

        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return trades

    def get_trades_by_emotional_state(self, emotional_state: str) -> List[Dict]:

        conn = get_connection()
        cursor = conn.execute("SELECT * FROM trades WHERE emotional_state = ? ORDER BY entry_date DESC", (emotional_state,))

        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return trades

    def get_open_trades(self) -> List[Dict]:

        conn = get_connection()
        cursor = conn.execute("SELECT * FROM trades WHERE outcome = 'open' ORDER BY entry_date DESC")

        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return trades

    def delete_trade(self, trade_id: int) -> bool:

        conn = get_connection()
        with conn:
            cursor = conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))

            deleted = cursor.rowcount > 0

        conn.close()

        if deleted:
            logger.info(f"Deleted trade id={trade_id}")
        return deleted

    def get_trades_as_dataframe(self):

        import pandas as pd

        engine = get_engine()

        query = """
            SELECT * FROM trades 
            WHERE outcome != 'open'
            ORDER BY entry_date ASC
        """

        df = pd.read_sql(query, engine)

        df["entry_date"] = pd.to_datetime(df["entry_date"])
        df["exit_date"] = pd.to_datetime(df["exit_date"])

        return df