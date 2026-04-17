from fastapi import FastAPI
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "tradingdb"),
        user=os.getenv("PGUSER", "tradinguser"),
        password=os.getenv("PGPASSWORD", ""),
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
