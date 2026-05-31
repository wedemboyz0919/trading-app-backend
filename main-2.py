from fastapi import FastAPI, HTTPException
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict

app = FastAPI()

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
        conn.close()
        return {"status": "connected", "version": row["version"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# One‑time DB setup route (call it once; then remove if you want)
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
        order_type TEXT NOT NULL CHECK (ordeOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol_algo ON paper_trades (symbol, algo_name);
    CREATE INDEX IF NOT EXISTS idx_live_trades_symbol_algo ON live_trades (symbol, algo_name);
    """

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "Tables and indexes created."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Payload model (simplified)
Payload = Dict

@app.post("", "price",
        "time_in_force", "exchange", "algo_name",
    ]
    missing = [k for k in required if k not in payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {missing}")

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
            RETonn.close()

        return {
            "status": "success",
            "id": row[0],
            "created_at": row[1].isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/live-trades" "time_in_force", "exchange", "algo_name",
    ]
    missing = [k for k in required if k not in payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {missing}")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            INSERT INTO live_trades (
                symbol, side, order_type, quantity, price,
                stop_price, time_in_force, exchange, algo_name
            ) VALUES (
                %(symbol)s, %(side)s, %(order_type)s, %(quantity)s, %(price)s,
                %(stop_price)s, %(time_in_force)s, %(exchange)s, %(algo_name)s
            )
            RETURNING id, created_at
        """
        cur.execute(sql, payload)
        row = cur.fetchone()
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "id": row[0],
            "created_at": row[1].isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}r_type IN ('LIMIT', 'MARKET', 'STOP', 'STOP_LIMIT')),
                quantity NUMERIC(16,8) NOT NULL,
                        price NUMERIC(16,8) NOT NULL,
                                stop_price NUMERIC(16,8),
                                     N
