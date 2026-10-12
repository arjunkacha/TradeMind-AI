from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.routers.auth import current_user
from pydantic import BaseModel, Field, model_validator

router = APIRouter(prefix="/api/simulator", tags=["Demo Trading Simulator"])
BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "simulator_migration_test.db"
STARTING_BALANCE = 10_000.0
BIQUOTE_BASE = "https://biquote.io/api"
ALLOWED_SYMBOLS = {"XAUUSD", "BTCUSD"}
ALLOWED_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
QUOTE_CACHE_SECONDS = 2.0
_quote_cache = {}


def now():
    return datetime.now(timezone.utc).isoformat()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY CHECK(id=1), balance REAL NOT NULL, currency TEXT NOT NULL DEFAULT 'USD')")
        c.execute("""CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY, symbol TEXT, side TEXT, order_type TEXT, quantity REAL,
            requested_price REAL, stop_loss REAL, take_profit REAL, status TEXT, created_at TEXT,
            position_id TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS positions (
            position_id TEXT PRIMARY KEY, order_id TEXT, symbol TEXT, side TEXT, quantity REAL,
            entry_price REAL, stop_loss REAL, take_profit REAL, opened_at TEXT, status TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY, position_id TEXT, symbol TEXT, side TEXT, quantity REAL,
            entry_price REAL, exit_price REAL, realized_pnl REAL, opened_at TEXT, closed_at TEXT,
            close_reason TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS auto_journal (
            journal_id TEXT PRIMARY KEY, trade_id TEXT UNIQUE NOT NULL, source TEXT NOT NULL,
            symbol TEXT, side TEXT, quantity REAL, entry_price REAL, exit_price REAL,
            realized_pnl REAL, opened_at TEXT, closed_at TEXT, close_reason TEXT,
            stop_loss REAL, take_profit REAL, holding_minutes REAL, r_multiple REAL,
            outcome TEXT, risk_score INTEGER, risk_level TEXT, decision TEXT,
            behaviors_json TEXT, ai_summary TEXT, lessons_json TEXT, created_at TEXT
        )""")
        # Safe, additive migrations: keep existing demo account, trades, and journal rows.
        migrations = {
            "orders": {
                "user_id": "INTEGER", "setup_type": "TEXT", "entry_reason": "TEXT", "emotion": "TEXT",
                "confidence": "INTEGER", "market_snapshot_json": "TEXT", "strategy_name": "TEXT"
            },
            "positions": {
                "user_id": "INTEGER", "setup_type": "TEXT", "entry_reason": "TEXT", "emotion": "TEXT",
                "confidence": "INTEGER", "market_snapshot_json": "TEXT", "strategy_name": "TEXT"
            },
            "trades": {
                "user_id": "INTEGER", "setup_type": "TEXT", "entry_reason": "TEXT", "emotion": "TEXT",
                "confidence": "INTEGER", "market_snapshot_json": "TEXT", "strategy_name": "TEXT"
            },
            "auto_journal": {
                "user_id": "INTEGER", "setup_type": "TEXT", "entry_reason": "TEXT", "emotion": "TEXT",
                "confidence": "INTEGER", "market_snapshot_json": "TEXT", "strategy_name": "TEXT"
            },
        }
        for table, columns in migrations.items():
            existing_columns = {row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()}
            for column, column_type in columns.items():
                if column not in existing_columns:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        c.execute("""
            CREATE TABLE IF NOT EXISTS simulator_accounts (
                user_id INTEGER PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 10000.0,
                currency TEXT NOT NULL DEFAULT 'USD',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        if c.execute("SELECT id FROM account WHERE id=1").fetchone() is None:
            c.execute("INSERT INTO account(id,balance,currency) VALUES(1,?,'USD')", (STARTING_BALANCE,))

        # Preserve legacy data by assigning it to the first registered user only
        # when it has not already been assigned. Never overwrite existing balances.
        legacy_user = c.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        if legacy_user is not None:
            legacy_user_id = int(legacy_user["id"])
            c.execute(
                """INSERT OR IGNORE INTO simulator_accounts (user_id, balance, currency)
                   SELECT ?, balance, currency FROM account WHERE id=1""",
                (legacy_user_id,),
            )
            for table in ("orders", "positions", "trades", "auto_journal"):
                c.execute(
                    f"UPDATE {table} SET user_id=? WHERE user_id IS NULL",
                    (legacy_user_id,),
                )


init_db()


def provider_get(path, params=None):
    url = f"{BIQUOTE_BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "TradeMind-AI-Demo/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = "biquote market-data provider returned an error"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("message") or payload.get("error") or detail
        except Exception:
            pass
        raise HTTPException(status_code=503, detail=f"Market data unavailable ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"Could not reach biquote market-data API: {exc}") from exc


class OrderIn(BaseModel):
    symbol: str = "XAUUSD"
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP"] = "MARKET"
    quantity: float = Field(gt=0, le=100)
    price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    setup_type: Optional[str] = Field(default=None, max_length=80)
    entry_reason: Optional[str] = Field(default=None, max_length=1000)
    emotion: Optional[str] = Field(default=None, max_length=40)
    confidence: Optional[int] = Field(default=None, ge=1, le=10)
    strategy_name: Optional[str] = Field(default=None, max_length=100)
    market_snapshot: Optional[dict] = None

    @model_validator(mode="after")
    def validate_order(self):
        self.symbol = self.symbol.upper()
        if self.symbol not in ALLOWED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {self.symbol}. Use XAUUSD or BTCUSD.")
        if self.order_type != "MARKET" and self.price is None:
            raise ValueError("Pending orders require a trigger price.")
        return self


class CloseIn(BaseModel):
    quantity: Optional[float] = Field(default=None, gt=0)


class ProtectionIn(BaseModel):
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)


def quote(symbol, require_fresh=False):
    symbol = symbol.upper()
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(404, "Unsupported symbol. Use XAUUSD or BTCUSD.")
    cached = _quote_cache.get(symbol)
    if cached and time.monotonic() - cached[0] < QUOTE_CACHE_SECONDS and not require_fresh:
        return dict(cached[1])
    params = {"allowStale": "false" if require_fresh else "true"}
    data = provider_get(urllib.parse.quote(symbol), params)
    required = ("bid", "ask")
    if any(data.get(k) is None for k in required):
        raise HTTPException(503, f"biquote returned an incomplete quote for {symbol}.")
    result = {
        "symbol": symbol,
        "bid": float(data["bid"]),
        "ask": float(data["ask"]),
        "mid": float(data.get("mid") or (float(data["bid"]) + float(data["ask"])) / 2),
        "spread": data.get("spread"),
        "timestamp": data.get("timestamp") or data.get("lastQuoteAt"),
        "source": "BIQUOTE",
        "provider_source": data.get("source"),
        "market_state": data.get("marketState", "unknown"),
        "stale": bool(data.get("stale", False)),
        "quote_age_seconds": data.get("quoteAgeSeconds"),
        "day_change_percent": data.get("dayDiffPercent"),
    }
    _quote_cache[symbol] = (time.monotonic(), result)
    return dict(result)


def pnl(side, entry, exit_price, quantity):
    return round((exit_price-entry) * quantity * (1 if side == "BUY" else -1), 2)


@router.get("/health")
def health():
    return {"status": "ok", "mode": "DEMO_ONLY", "quote_source": "BIQUOTE", "symbols": sorted(ALLOWED_SYMBOLS),
            "note": "Live market data is external. Demo-only orders; SL/TP triggers are checked when positions are refreshed. Pending order triggers are not implemented."}


@router.get("/symbols")
def symbols():
    return {"symbols": [{"symbol": s, "source": "BIQUOTE"} for s in sorted(ALLOWED_SYMBOLS)]}


@router.get("/market/quote")
def market_quote(symbol: str = Query("XAUUSD")):
    return quote(symbol)


@router.get("/market/candles")
def market_candles(
    symbol: str = Query("XAUUSD"),
    interval: str = Query("5m"),
    limit: int = Query(200, ge=1, le=1000),
    from_time: Optional[str] = Query(default=None, alias="from"),
    to_time: Optional[str] = Query(default=None, alias="to"),
):
    """Return provider candles, optionally for a specific historical time range.

    The provider caps each response at 1,000 bars. Clients should page through
    long histories using successive `from`/`to` windows rather than asking for
    an entire year of 5-minute candles in one request.
    """
    symbol = symbol.upper()
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(404, "Unsupported symbol. Use XAUUSD or BTCUSD.")
    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(422, f"Unsupported interval. Use one of: {', '.join(sorted(ALLOWED_INTERVALS))}.")

    def parse_iso(value: str, field: str) -> datetime:
        try:
            # Accept ISO-8601 timestamps with either Z or an explicit offset.
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, f"'{field}' must be a valid ISO-8601 date or timestamp.") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    if (from_time is None) != (to_time is None):
        raise HTTPException(422, "Provide both 'from' and 'to' for a historical range.")
    if from_time is not None and to_time is not None:
        start_dt = parse_iso(from_time, "from")
        end_dt = parse_iso(to_time, "to")
        if end_dt <= start_dt:
            raise HTTPException(422, "'to' must be later than 'from'.")
        # Normalize provider inputs to explicit UTC ISO timestamps.
        params = {
            "interval": interval,
            "limit": limit,
            "from": start_dt.isoformat().replace("+00:00", "Z"),
            "to": end_dt.isoformat().replace("+00:00", "Z"),
        }
    else:
        params = {"interval": interval, "limit": limit}

    data = provider_get(f"{urllib.parse.quote(symbol)}/ohlc", params)
    bars = data.get("bars")
    if not isinstance(bars, list):
        raise HTTPException(503, "biquote returned an invalid candle response.")
    return {
        "symbol": symbol,
        "interval": interval,
        "source": "BIQUOTE",
        "bars": bars,
        "count": len(bars),
        "requested_from": params.get("from"),
        "requested_to": params.get("to"),
        "timestamp": now(),
    }


@router.get("/account")
def account(user=Depends(current_user)):
    user_id = int(user["id"])
    with db() as c:
        c.execute(
            """INSERT OR IGNORE INTO simulator_accounts (user_id, balance, currency)
               VALUES (?, ?, 'USD')""",
            (user_id, STARTING_BALANCE),
        )
        a_row = c.execute(
            "SELECT user_id AS id, balance, currency FROM simulator_accounts WHERE user_id=?",
            (user_id,),
        ).fetchone()
        a = dict(a_row)
        positions = c.execute(
            "SELECT * FROM positions WHERE user_id=? AND status='OPEN'",
            (user_id,),
        ).fetchall()
        unrealized = 0.0
        quote_errors = []
        for p in positions:
            try:
                q = quote(p["symbol"])
                mark = q["bid"] if p["side"] == "BUY" else q["ask"]
                unrealized += pnl(p["side"], p["entry_price"], mark, p["quantity"])
            except HTTPException as exc:
                quote_errors.append({"symbol": p["symbol"], "detail": exc.detail})
        realized_row = c.execute(
            "SELECT COALESCE(SUM(realized_pnl), 0) AS realized_pnl FROM trades WHERE user_id=?",
            (user_id,),
        ).fetchone()
        realized = float(realized_row["realized_pnl"] or 0.0)
        a["realized_pnl"] = round(realized, 2)
        a["unrealized_pnl"] = round(unrealized, 2)
        a["total_pnl"] = round((float(a["balance"]) - STARTING_BALANCE) + unrealized, 2)
        a["equity"] = round(a["balance"] + unrealized, 2)
        a["open_positions"] = len(positions)
        a["quote_errors"] = quote_errors
        return a


@router.post("/orders")
def place_order(order: OrderIn, user=Depends(current_user)):
    user_id = int(user["id"])
    q = quote(order.symbol, require_fresh=(order.order_type == "MARKET"))
    if q.get("stale") or q.get("market_state") == "closed":
        raise HTTPException(503, "A fresh market quote is not available. No demo order was placed.")
    oid = "SIM-ORD-" + uuid.uuid4().hex[:12].upper()
    posid = None
    status = "PENDING" if order.order_type != "MARKET" else "FILLED"
    entry = None
    if status == "FILLED":
        entry = q["ask"] if order.side == "BUY" else q["bid"]
        if order.stop_loss is not None:
            if order.side == "BUY" and order.stop_loss >= entry:
                raise HTTPException(422, "BUY stop-loss must be below entry.")
            if order.side == "SELL" and order.stop_loss <= entry:
                raise HTTPException(422, "SELL stop-loss must be above entry.")
        if order.take_profit is not None:
            if order.side == "BUY" and order.take_profit <= entry:
                raise HTTPException(422, "BUY take-profit must be above entry.")
            if order.side == "SELL" and order.take_profit >= entry:
                raise HTTPException(422, "SELL take-profit must be below entry.")
        posid = "SIM-POS-" + uuid.uuid4().hex[:12].upper()
    created_at = now()
    snapshot_json = json.dumps(order.market_snapshot, ensure_ascii=False) if order.market_snapshot else None
    context_values = (order.setup_type, order.entry_reason, order.emotion, order.confidence, snapshot_json, order.strategy_name)
    with db() as c:
        c.execute("""INSERT INTO orders
            (order_id,user_id,symbol,side,order_type,quantity,requested_price,stop_loss,take_profit,status,created_at,position_id,
             setup_type,entry_reason,emotion,confidence,market_snapshot_json,strategy_name)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (oid, user_id, order.symbol, order.side, order.order_type, order.quantity, order.price,
             order.stop_loss, order.take_profit, status, created_at, posid, *context_values))
        if posid:
            c.execute("""INSERT INTO positions
                (position_id,user_id,order_id,symbol,side,quantity,entry_price,stop_loss,take_profit,opened_at,status,
                 setup_type,entry_reason,emotion,confidence,market_snapshot_json,strategy_name)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (posid, user_id, oid, order.symbol, order.side, order.quantity, entry, order.stop_loss,
                 order.take_profit, created_at, "OPEN", *context_values))
    return {"order_id": oid, "position_id": posid, "symbol": order.symbol, "side": order.side,
            "order_type": order.order_type, "quantity": order.quantity, "status": status,
            "fill_price": entry, "quote_source": "BIQUOTE", "execution_mode": "DEMO_ONLY",
            "message": "Demo market order simulated using the latest biquote quote." if status == "FILLED" else
                       "Pending order stored; trigger monitoring is not implemented yet."}


@router.get("/orders")
def orders(limit: int = Query(100, ge=1, le=500), user=Depends(current_user)):
    user_id = int(user["id"])
    with db() as c:
        rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return {"count": len(rows), "orders": [dict(r) for r in rows]}


def create_auto_journal(c, trade, stop_loss=None, take_profit=None):
    """Create one durable journal record for each realized exit/partial exit.

    Insights are generated from the simulator's own execution facts. They are
    transparent rule-based coaching, not a claim that a trained model inferred
    hidden intent or psychology.
    """
    trade_id = trade["trade_id"]
    existing = c.execute("SELECT journal_id FROM auto_journal WHERE trade_id=?", (trade_id,)).fetchone()
    if existing:
        return
    entry = float(trade["entry_price"])
    exit_price = float(trade["exit_price"])
    quantity = float(trade["quantity"])
    realized = float(trade["realized_pnl"])
    side = str(trade["side"]).upper()
    close_reason = str(trade.get("close_reason") or "MANUAL").upper()
    setup_type = trade.get("setup_type")
    entry_reason = trade.get("entry_reason")
    emotion = trade.get("emotion")
    confidence = trade.get("confidence")
    strategy_name = trade.get("strategy_name")
    snapshot_json = trade.get("market_snapshot_json")
    if not snapshot_json and trade.get("market_snapshot"):
        snapshot_json = json.dumps(trade.get("market_snapshot"), ensure_ascii=False)
    opened_at = trade.get("opened_at")
    closed_at = trade.get("closed_at") or now()
    try:
        opened_dt = datetime.fromisoformat(str(opened_at).replace("Z", "+00:00"))
        closed_dt = datetime.fromisoformat(str(closed_at).replace("Z", "+00:00"))
        holding_minutes = max(0.0, (closed_dt - opened_dt).total_seconds() / 60)
    except (TypeError, ValueError):
        holding_minutes = None

    risk_amount = abs(entry - float(stop_loss)) * quantity if stop_loss is not None else 0.0
    r_multiple = round(realized / risk_amount, 2) if risk_amount > 0 else None
    outcome = "WIN" if realized > 0 else "LOSS" if realized < 0 else "BREAKEVEN"
    behaviors = []
    lessons = []
    if stop_loss is None:
        behaviors.append("No Stop Loss")
        lessons.append("A stop-loss was not attached to this position; define invalidation and maximum loss before entry.")
    if close_reason == "STOP_LOSS":
        behaviors.append("Stop-Loss Exit")
        lessons.append("The stop-loss was reached. Review whether the entry thesis and stop placement matched your setup rules.")
    elif close_reason == "TAKE_PROFIT":
        behaviors.append("Take-Profit Exit")
        lessons.append("The take-profit was reached. Review whether the target was planned from a clear risk/reward level.")
    elif close_reason == "MANUAL":
        behaviors.append("Manual Exit")
        lessons.append("Compare the manual exit with your original trade thesis and planned exit criteria.")
    if not entry_reason or not str(entry_reason).strip():
        behaviors.append("Missing Entry Thesis")
        lessons.append("Write the setup trigger and invalidation before entering; this makes post-trade review testable.")
    if emotion and str(emotion).upper() in {"REVENGE", "FRUSTRATED", "FOMO", "ANXIOUS", "FEARFUL"}:
        behaviors.append("Self-Reported Emotional Entry")
        lessons.append(f"You recorded your entry emotion as {emotion}. Compare this entry with your written setup rules before repeating it.")
    if confidence is not None and int(confidence) <= 3:
        behaviors.append("Low Entry Confidence")
        lessons.append("Confidence was 3/10 or lower. Define a minimum setup-quality threshold and check it before entering.")
    if realized < 0:
        lessons.append("Record what market condition invalidated the trade and one rule to follow on the next similar setup.")
    elif realized > 0:
        lessons.append("Identify which part of the setup worked; repeat the process rather than chasing the outcome.")
    else:
        lessons.append("Review whether the trade followed the plan even though the result was near breakeven.")

    risk_score = 65 if stop_loss is None else 35
    if quantity >= 1:
        risk_score += 10
    risk_score = max(0, min(100, risk_score))
    risk_level = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 35 else "LOW"
    decision = "REVIEW" if realized < 0 or stop_loss is None else "PLAN FOLLOWED â€” REVIEW"
    pnl_text = f"{realized:+.2f} USD"
    reason_text = close_reason.replace("_", " ").lower()
    ai_summary = (
        f"{side} {trade['symbol']} closed via {reason_text} with {pnl_text} realized P&L. "
        f"Entry {entry:g}, exit {exit_price:g}, quantity {quantity:g}. "
        + (f"Held for approximately {holding_minutes:.1f} minutes. " if holding_minutes is not None else "")
        + (f"Result: {r_multiple:+.2f}R against the attached stop distance." if r_multiple is not None
           else "R-multiple is unavailable because no valid stop-loss distance was recorded.")
        + (f" Setup: {setup_type}." if setup_type else "")
        + (f" Entry thesis: {str(entry_reason).strip()}" if entry_reason else " Entry thesis was not recorded.")
        + (f" Self-reported entry emotion: {emotion}." if emotion else "")
        + (f" Entry confidence: {confidence}/10." if confidence is not None else "")
    )
    c.execute("""INSERT OR IGNORE INTO auto_journal
        (journal_id, user_id, trade_id, source, symbol, side, quantity, entry_price, exit_price,
         realized_pnl, opened_at, closed_at, close_reason, stop_loss, take_profit,
         holding_minutes, r_multiple, outcome, risk_score, risk_level, decision,
         behaviors_json, ai_summary, lessons_json, created_at,
         setup_type, entry_reason, emotion, confidence, market_snapshot_json, strategy_name)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("SIM-JRN-" + uuid.uuid4().hex[:12].upper(), trade.get("user_id"), trade_id, "simulator_auto",
         trade["symbol"], side, quantity, entry, exit_price, realized, opened_at,
         closed_at, close_reason, stop_loss, take_profit, holding_minutes, r_multiple,
         outcome, risk_score, risk_level, decision, json.dumps(behaviors),
         ai_summary, json.dumps(lessons), now(), setup_type, entry_reason, emotion,
         confidence, snapshot_json, strategy_name))


def backfill_auto_journal():
    """Backfill journal entries for simulator trades closed before this update."""
    with db() as c:
        rows = c.execute("SELECT * FROM trades ORDER BY closed_at ASC").fetchall()
        for row in rows:
            trade = dict(row)
            pos = c.execute(
                "SELECT stop_loss, take_profit FROM positions WHERE position_id=?",
                (trade.get("position_id"),),
            ).fetchone()
            protection = dict(pos) if pos else {}
            trade.update({k: protection.get(k) for k in ("setup_type", "entry_reason", "emotion", "confidence", "market_snapshot_json", "strategy_name")})
            create_auto_journal(c, trade, protection.get("stop_loss"), protection.get("take_profit"))


def journal_record(row):
    item = dict(row)
    item["trade_id"] = item.get("trade_id") or item.get("journal_id")
    item["id"] = item["trade_id"]
    item["direction"] = item.get("side")
    item["net_pnl"] = item.get("realized_pnl")
    item["pnl"] = item.get("realized_pnl")
    item["entry_time"] = item.get("opened_at")
    item["exit_time"] = item.get("closed_at")
    item["behaviors"] = ", ".join(json.loads(item.get("behaviors_json") or "[]"))
    item["lessons"] = json.loads(item.get("lessons_json") or "[]")
    try:
        item["market_snapshot"] = json.loads(item.get("market_snapshot_json") or "null")
    except (TypeError, json.JSONDecodeError):
        item["market_snapshot"] = None
    item["behaviorRecords"] = [
        {"behavior": b, "severity": item.get("risk_level", "MEDIUM"),
         "score": item.get("risk_score", 0), "evidence": "Inferred from recorded execution fields."}
        for b in json.loads(item.get("behaviors_json") or "[]")
    ]
    item["ml_win_probability"] = None
    item["journal_engine"] = "TradeMind Auto-Journal (execution-based coaching)"
    return item


def execute_triggered_exits(user_id: int):
    """Check attached SL/TP against fresh provider quotes; demo-only execution."""
    with db() as c:
        rows = c.execute("SELECT * FROM positions WHERE user_id=? AND status='OPEN'", (user_id,)).fetchall()
        for row in rows:
            p = dict(row)
            if p["stop_loss"] is None and p["take_profit"] is None:
                continue
            try:
                q = quote(p["symbol"], require_fresh=True)
            except HTTPException:
                continue
            if q.get("stale") or q.get("market_state") == "closed":
                continue
            mark = q["bid"] if p["side"] == "BUY" else q["ask"]
            reason = None
            if p["side"] == "BUY":
                if p["stop_loss"] is not None and mark <= p["stop_loss"]:
                    reason = "STOP_LOSS"
                elif p["take_profit"] is not None and mark >= p["take_profit"]:
                    reason = "TAKE_PROFIT"
            else:
                if p["stop_loss"] is not None and mark >= p["stop_loss"]:
                    reason = "STOP_LOSS"
                elif p["take_profit"] is not None and mark <= p["take_profit"]:
                    reason = "TAKE_PROFIT"
            if not reason:
                continue
            realized = pnl(p["side"], p["entry_price"], mark, p["quantity"])
            closed_at = now()
            tid = "SIM-TRD-" + uuid.uuid4().hex[:12].upper()
            context_keys = ("setup_type", "entry_reason", "emotion", "confidence", "market_snapshot_json", "strategy_name")
            context = {key: p.get(key) for key in context_keys}
            c.execute("""INSERT INTO trades
                (trade_id,user_id,position_id,symbol,side,quantity,entry_price,exit_price,realized_pnl,opened_at,closed_at,close_reason,
                 setup_type,entry_reason,emotion,confidence,market_snapshot_json,strategy_name)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid, user_id, p["position_id"], p["symbol"], p["side"], p["quantity"], p["entry_price"], mark,
                 realized, p["opened_at"], closed_at, reason, *[context[k] for k in context_keys]))
            create_auto_journal(c, {
                "trade_id": tid, "user_id": user_id, "position_id": p["position_id"], "symbol": p["symbol"],
                "side": p["side"], "quantity": p["quantity"], "entry_price": p["entry_price"],
                "exit_price": mark, "realized_pnl": realized, "opened_at": p["opened_at"],
                "closed_at": closed_at, "close_reason": reason, **context,
            }, p["stop_loss"], p["take_profit"])
            c.execute("UPDATE simulator_accounts SET balance=balance+? WHERE user_id=?", (realized, user_id))
            c.execute("UPDATE positions SET quantity=0,status='CLOSED' WHERE position_id=? AND user_id=?", (p["position_id"], user_id))


@router.get("/positions")
def positions(user=Depends(current_user)):
    user_id = int(user["id"])
    execute_triggered_exits(user_id)
    with db() as c:
        rows = c.execute("SELECT * FROM positions WHERE user_id=? AND status='OPEN' ORDER BY opened_at DESC", (user_id,)).fetchall()
    result = []
    for row in rows:
        p = dict(row)
        try:
            q = quote(p["symbol"])
            mark = q["bid"] if p["side"] == "BUY" else q["ask"]
            p["mark_price"] = mark
            p["unrealized_pnl"] = pnl(p["side"], p["entry_price"], mark, p["quantity"])
            p["quote_source"] = "BIQUOTE"
            p["quote_stale"] = q.get("stale", False)
            p["quote_timestamp"] = q.get("timestamp")
        except HTTPException as exc:
            p["mark_price"] = None
            p["unrealized_pnl"] = None
            p["quote_source"] = "UNAVAILABLE"
            p["quote_error"] = exc.detail
        result.append(p)
    return {"count": len(result), "positions": result}


@router.put("/positions/{position_id}/protection")
def update_protection(position_id: str, request: ProtectionIn, user=Depends(current_user)):
    user_id = int(user["id"])
    with db() as c:
        row = c.execute("SELECT * FROM positions WHERE position_id=? AND user_id=? AND status='OPEN'", (position_id, user_id)).fetchone()
        if row is None:
            raise HTTPException(404, "Open position not found.")
        p = dict(row)
        sl, tp = request.stop_loss, request.take_profit
        if sl is not None:
            if p["side"] == "BUY" and sl >= p["entry_price"]:
                raise HTTPException(422, "For a BUY position, stop-loss must be below entry price.")
            if p["side"] == "SELL" and sl <= p["entry_price"]:
                raise HTTPException(422, "For a SELL position, stop-loss must be above entry price.")
        if tp is not None:
            if p["side"] == "BUY" and tp <= p["entry_price"]:
                raise HTTPException(422, "For a BUY position, take-profit must be above entry price.")
            if p["side"] == "SELL" and tp >= p["entry_price"]:
                raise HTTPException(422, "For a SELL position, take-profit must be below entry price.")
        c.execute("UPDATE positions SET stop_loss=?, take_profit=? WHERE position_id=? AND user_id=?", (sl, tp, position_id, user_id))
        c.execute("UPDATE orders SET stop_loss=?, take_profit=? WHERE order_id=? AND user_id=?", (sl, tp, p["order_id"], user_id))
    return {"position_id": position_id, "stop_loss": sl, "take_profit": tp, "status": "UPDATED", "execution_mode": "DEMO_ONLY"}


@router.post("/positions/{position_id}/close")
def close_position(position_id: str, request: CloseIn, user=Depends(current_user)):
    user_id = int(user["id"])
    with db() as c:
        row = c.execute("SELECT * FROM positions WHERE position_id=? AND user_id=? AND status='OPEN'", (position_id, user_id)).fetchone()
        if row is None:
            raise HTTPException(404, "Open position not found.")
        p = dict(row)
        qty = request.quantity if request.quantity is not None else p["quantity"]
        if qty > p["quantity"] + 1e-9:
            raise HTTPException(422, "Close quantity exceeds open quantity.")
        q = quote(p["symbol"], require_fresh=True)
        if q.get("stale") or q.get("market_state") == "closed":
            raise HTTPException(503, "A fresh market quote is not available. Position was not closed.")
        exit_price = q["bid"] if p["side"] == "BUY" else q["ask"]
        realized = pnl(p["side"], p["entry_price"], exit_price, qty)
        remaining = round(p["quantity"] - qty, 8)
        closed_at = now()
        tid = "SIM-TRD-" + uuid.uuid4().hex[:12].upper()
        context_keys = ("setup_type", "entry_reason", "emotion", "confidence", "market_snapshot_json", "strategy_name")
        context = {key: p.get(key) for key in context_keys}
        c.execute("""INSERT INTO trades
            (trade_id,user_id,position_id,symbol,side,quantity,entry_price,exit_price,realized_pnl,opened_at,closed_at,close_reason,
             setup_type,entry_reason,emotion,confidence,market_snapshot_json,strategy_name)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, user_id, position_id, p["symbol"], p["side"], qty, p["entry_price"], exit_price,
             realized, p["opened_at"], closed_at, "MANUAL", *[context[k] for k in context_keys]))
        create_auto_journal(c, {
            "trade_id": tid, "user_id": user_id, "position_id": position_id, "symbol": p["symbol"],
            "side": p["side"], "quantity": qty, "entry_price": p["entry_price"],
            "exit_price": exit_price, "realized_pnl": realized, "opened_at": p["opened_at"],
            "closed_at": closed_at, "close_reason": "MANUAL", **context,
        }, p["stop_loss"], p["take_profit"])
        c.execute("UPDATE simulator_accounts SET balance=balance+? WHERE user_id=?", (realized, user_id))
        if remaining <= 1e-8:
            c.execute("UPDATE positions SET quantity=0,status='CLOSED' WHERE position_id=? AND user_id=?", (position_id, user_id))
        else:
            c.execute("UPDATE positions SET quantity=? WHERE position_id=? AND user_id=?", (remaining, position_id, user_id))
    return {"trade_id": tid, "position_id": position_id, "symbol": p["symbol"], "side": p["side"],
            "closed_quantity": qty, "remaining_quantity": max(remaining, 0), "entry_price": p["entry_price"],
            "exit_price": exit_price, "realized_pnl": realized, "closed_at": closed_at,
            "close_reason": "MANUAL", "quote_source": "BIQUOTE", "execution_mode": "DEMO_ONLY"}


@router.get("/journal")
def auto_journal(limit: int = Query(200, ge=1, le=1000), user=Depends(current_user)):
    user_id = int(user["id"])
    """Automatically generated journal entries for closed simulator trades."""
    with db() as c:
        rows = c.execute("SELECT * FROM auto_journal WHERE user_id=? ORDER BY closed_at DESC LIMIT ?", (user_id, limit)).fetchall()
    entries = [journal_record(row) for row in rows]
    return {"count": len(entries), "journal": entries, "source": "simulator_auto"}


@router.get("/journal/insights")
def journal_insights(limit: int = Query(100, ge=1, le=500), user=Depends(current_user)):
    user_id = int(user["id"])
    """Account-level descriptive insights based only on recorded simulator exits."""
    with db() as c:
        rows = c.execute("SELECT * FROM auto_journal WHERE user_id=? ORDER BY closed_at DESC LIMIT ?", (user_id, limit)).fetchall()
    entries = [journal_record(row) for row in rows]
    if not entries:
        return {"count": 0, "summary": {"trades": 0, "win_rate": 0, "net_pnl": 0}, "insights": ["Close a demo trade to start building personalized insights."], "source": "simulator_auto"}
    total = len(entries)
    wins = sum(1 for e in entries if (e.get("realized_pnl") or 0) > 0)
    losses = sum(1 for e in entries if (e.get("realized_pnl") or 0) < 0)
    net = round(sum(float(e.get("realized_pnl") or 0) for e in entries), 2)
    r_values = [float(e["r_multiple"]) for e in entries if e.get("r_multiple") is not None]
    no_sl = sum(1 for e in entries if e.get("stop_loss") is None)
    stop_exits = sum(1 for e in entries if e.get("close_reason") == "STOP_LOSS")
    setups = {}
    emotions = {}
    for e in entries:
        setup = e.get("setup_type") or "Unspecified setup"
        bucket = setups.setdefault(setup, {"trades": 0, "wins": 0, "net_pnl": 0.0})
        bucket["trades"] += 1
        bucket["wins"] += int((e.get("realized_pnl") or 0) > 0)
        bucket["net_pnl"] += float(e.get("realized_pnl") or 0)
        emotion = e.get("emotion")
        if emotion:
            eb = emotions.setdefault(emotion, {"trades": 0, "net_pnl": 0.0})
            eb["trades"] += 1
            eb["net_pnl"] += float(e.get("realized_pnl") or 0)
    insights = []
    if no_sl:
        insights.append(f"{no_sl}/{total} recorded exits ({no_sl/total:.0%}) had no stop-loss saved. Consider defining invalidation before entry.")
    if stop_exits:
        insights.append(f"{stop_exits}/{total} exits were stop-loss exits. Compare their entry thesis and market snapshot to identify repeatable setup failures.")
    if r_values:
        avg_r = sum(r_values) / len(r_values)
        insights.append(f"Average recorded R-multiple is {avg_r:+.2f}R across {len(r_values)} trades with a valid stop distance.")
    if setups:
        ranked = sorted(setups.items(), key=lambda kv: (kv[1]["net_pnl"], kv[1]["trades"]), reverse=True)
        name, stats = ranked[0]
        if stats["trades"] >= 2:
            insights.append(f"Best net-P&L setup in this sample: {name} ({stats['trades']} trades, {stats['net_pnl']:+.2f} USD). Small samples are not reliable proof of an edge.")
    emotional = [(k,v) for k,v in emotions.items() if k.upper() in {"REVENGE","FRUSTRATED","FOMO","ANXIOUS","FEARFUL"}]
    for emotion, stats in emotional:
        insights.append(f"You self-reported {emotion} on {stats['trades']} trade(s), net P&L {stats['net_pnl']:+.2f} USD. Review these separately; this is self-reported context, not inferred psychology.")
    if not insights:
        insights.append("No repeated risk pattern stands out in the current sample yet. Keep recording setup, thesis, emotion, and confidence on each entry.")
    return {"count": total, "summary": {"trades": total, "wins": wins, "losses": losses,
            "win_rate": round(wins / total * 100, 1), "net_pnl": net,
            "average_r": round(sum(r_values) / len(r_values), 2) if r_values else None,
            "trades_with_r": len(r_values), "without_stop_loss": no_sl},
            "setups": [{"setup_type": k, "trades": v["trades"], "wins": v["wins"], "win_rate": round(v["wins"]/v["trades"]*100,1), "net_pnl": round(v["net_pnl"],2)} for k,v in setups.items()],
            "insights": insights, "source": "simulator_auto", "method": "descriptive rules over recorded closed trades; not an ML prediction"}



@router.get("/journal/{trade_id}")
def auto_journal_detail(trade_id: str, user=Depends(current_user)):
    user_id = int(user["id"])
    with db() as c:
        row = c.execute("SELECT * FROM auto_journal WHERE user_id=? AND (trade_id=? OR journal_id=?)", (user_id, trade_id, trade_id)).fetchone()
    if row is None:
        raise HTTPException(404, "Auto-journal entry not found.")
    return {"journal": journal_record(row)}


@router.get("/trades")
def trades(limit: int = Query(200, ge=1, le=1000), user=Depends(current_user)):
    user_id = int(user["id"])
    with db() as c:
        rows = c.execute("SELECT * FROM trades WHERE user_id=? ORDER BY closed_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return {"count": len(rows), "trades": [dict(r) for r in rows]}


# Existing simulator exits are journaled once on backend startup as well.
backfill_auto_journal()

