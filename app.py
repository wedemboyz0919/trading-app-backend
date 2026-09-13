from decimal import Decimal
from enum import Enum
import os
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator


app = FastAPI(
    title="Trading App Backend",
    version="0.2.0",
    description="Paper-trading API with PostgreSQL storage and validated order requests.",
)


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"


class PaperTradeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: Side
    order_type: OrderType
    quantity: Decimal = Field(gt=0, max_digits=16, decimal_places=8)
    price: Decimal = Field(
        gt=0,
        max_digits=16,
        decimal_places=8,
        description="Reference price for MARKET orders; limit price for LIMIT orders.",
    )
    stop_price: Optional[Decimal] = Field(
        default=None, gt=0, max_digits=16, decimal_places=8
    )
    time_in_force: TimeInForce
    exchange: str = Field(min_length=1, max_length=30)
    algo_name: str = Field(min_length=1, max_length=100)

    @field_validator("symbol", "exchange", mode="before")
    @classmethod
    def normalize_uppercase(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("algo_name", mode="before")
    @classmethod
    def normalize_algo_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_stop_price(self) -> "PaperTradeRequest":
        if self.order_type in {OrderType.STOP, OrderType.STOP_LIMIT}:
            if self.stop_price is None:
                raise ValueError(
                    "stop_price is required for STOP and STOP_LIMIT orders"
                )
        elif self.stop_price is not None:
            raise ValueError(
                "stop_price is only allowed for STOP and STOP_LIMIT orders"
            )
        return self


def get_db_connection():
    hostname = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    database = os.getenv("PGDATABASE")
    username = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")

    if None in [hostname, port, database, username, password]:
        raise ValueError("Missing required DB env vars; tradingdb-app secret is missing.")

    return psycopg2.connect(
        host=hostname,
        port=port,
        database=database,
        user=username,
        password=password,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/db-test")
def db_test():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT version();")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "connected", "version": row["version"]}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection is unavailable.",
        )


@app.post("/api/db-setup")
def db_setup():
    sql = """
    CREATE TABLE IF NOT EXISTS paper_trades (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
        order_type TEXT NOT NULL CHECK (order_type IN ('LIMIT', 'MARKET', 'STOP', 'STOP_LIMIT')),
        quantity NUMERIC(16,8) NOT NULL,
        price NUMERIC(16,8) NOT NULL,
        stop_price NUMERIC(16,8),
        time_in_force TEXT NOT NULL,
        exchange TEXT NOT NULL,
        algo_name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS live_trades (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
        order_type TEXT NOT NULL CHECK (order_type IN ('LIMIT', 'MARKET', 'STOP', 'STOP_LIMIT')),
        quantity NUMERIC(16,8) NOT NULL,
        price NUMERIC(16,8) NOT NULL,
        stop_price NUMERIC(16,8),
        time_in_force TEXT NOT NULL,
        exchange TEXT NOT NULL,
        algo_name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol_algo
        ON paper_trades (symbol, algo_name);
    CREATE INDEX IF NOT EXISTS idx_live_trades_symbol_algo
        ON live_trades (symbol, algo_name);
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok", "message": "Tables and indexes created."}
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Database setup failed.",
        )


@app.get("/api/paper-trades")
def list_paper_trades():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM paper_trades ORDER BY id DESC;")
        trades = cur.fetchall()
        cur.close()
        conn.close()
        return {"status": "success", "trades": [dict(trade) for trade in trades]}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve paper trades.",
        )


@app.post("/api/paper-trades", status_code=201)
def create_paper_trade(trade: PaperTradeRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            INSERT INTO paper_trades (
                symbol, side, order_type, quantity, price,
                stop_price, time_in_force, exchange, algo_name
            ) VALUES (
                %(symbol)s, %(side)s, %(order_type)s, %(quantity)s, %(price)s,
                %(stop_price)s, %(time_in_force)s, %(exchange)s, %(algo_name)s
            )
            RETURNING id, created_at
        """
        params = trade.model_dump()
        params["side"] = trade.side.value
        params["order_type"] = trade.order_type.value
        params["time_in_force"] = trade.time_in_force.value

        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {
            "status": "success",
            "id": row[0],
            "created_at": row[1].isoformat(),
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to create paper trade.",
        )


@app.post("/api/live-trades", status_code=501)
def create_live_trade(_: PaperTradeRequest):
    raise HTTPException(
        status_code=501,
        detail="Live trading is not implemented. Use /api/paper-trades.",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000)
