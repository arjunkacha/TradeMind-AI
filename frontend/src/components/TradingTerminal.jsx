import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { CandlestickSeries, ColorType, createChart } from "lightweight-charts";
import { Activity, AlertCircle, ArrowDownRight, ArrowUpRight, CheckCircle2, Clock3, RefreshCw, ShieldCheck, Wallet, X } from "lucide-react";
import "./TradingTerminal.css";

const API = "http://127.0.0.1:8000/api/simulator";
const client = axios.create({ baseURL: API, timeout: 10000 });
const SYMBOLS = ["XAUUSD", "BTCUSD"];
const INTERVAL_SECONDS = { "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400 };
const EMPTY_QUOTES = {
  XAUUSD: { symbol: "XAUUSD", bid: null, ask: null, source: "UNAVAILABLE", stale: true },
  BTCUSD: { symbol: "BTCUSD", bid: null, ask: null, source: "UNAVAILABLE", stale: true },
};
const money = (v) => Number(v || 0).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num = (v, digits = 2) => Number(v || 0).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

function CandleChart({ candles, loading, error, positions, symbol, interval }) {
  const host = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const priceLinesRef = useRef([]);
  useEffect(() => {
    if (!host.current) return;
    const chart = createChart(host.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "#0b1220" }, textColor: "#8ea0b8", fontFamily: "Inter, system-ui, sans-serif" },
      grid: { vertLines: { color: "#172235" }, horzLines: { color: "#172235" } },
      rightPriceScale: { borderColor: "#243249" },
      timeScale: { borderColor: "#243249", timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: "#64748b" }, horzLine: { color: "#64748b" } },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e", downColor: "#ef4444", borderUpColor: "#22c55e", borderDownColor: "#ef4444", wickUpColor: "#22c55e", wickDownColor: "#ef4444",
    });
    chartRef.current = chart;
    seriesRef.current = series;
    const observer = new ResizeObserver(() => chart.applyOptions({ width: host.current?.clientWidth || 600, height: host.current?.clientHeight || 340 }));
    observer.observe(host.current);
    return () => { observer.disconnect(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);
  const loadedSymbolRef = useRef(null);
  const lastAppliedCandlesRef = useRef([]);

  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !candles.length) return;

    const previous = lastAppliedCandlesRef.current;
    const isNewSymbol = loadedSymbolRef.current !== symbol;
    const needsFullReload =
      isNewSymbol ||
      previous.length === 0 ||
      candles[0]?.time !== previous[0]?.time ||
      candles.length < previous.length;

    if (needsFullReload) {
      // Load the complete candle history received from the provider.
      // Only the initial viewport is focused on the latest ~80 bars; older
      // candles remain in the chart and can be reached by scrolling left.
      series.setData(candles);
      const visibleCount = Math.min(80, candles.length);
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, candles.length - visibleCount),
        to: candles.length + 3,
      });
      loadedSymbolRef.current = symbol;
      lastAppliedCandlesRef.current = candles;
      return;
    }

    // Incrementally update only the current/new candles. Calling setData +
    // fitContent on every poll resets the user's viewport and feels like
    // history is disappearing. series.update preserves zoom and scroll.
    const previousLastTime = previous[previous.length - 1]?.time ?? 0;
    const updates = candles.filter((candle) => candle.time >= previousLastTime);
    updates.forEach((candle) => series.update(candle));
    lastAppliedCandlesRef.current = candles;
  }, [candles, symbol]);
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    priceLinesRef.current.forEach((line) => { try { series.removePriceLine(line); } catch {} });
    priceLinesRef.current = [];
    const active = (positions || []).filter((p) => p.symbol === symbol);
    active.forEach((p) => {
      const addLine = (price, title, color, lineStyle = 2) => {
        const value = Number(price);
        if (!Number.isFinite(value) || value <= 0) return;
        priceLinesRef.current.push(series.createPriceLine({ price: value, title, color, lineWidth: 2, lineStyle, axisLabelVisible: true }));
      };
      addLine(p.entry_price, `${p.side} ENTRY · ${Number(p.quantity).toFixed(4)}`, p.side === "BUY" ? "#60a5fa" : "#c084fc", 0);
      if (p.stop_loss != null) addLine(p.stop_loss, `SL · ${p.position_id.slice(-6)}`, "#ef4444", 2);
      if (p.take_profit != null) addLine(p.take_profit, `TP · ${p.position_id.slice(-6)}`, "#22c55e", 2);
    });
    return () => {
      priceLinesRef.current.forEach((line) => { try { series.removePriceLine(line); } catch {} });
      priceLinesRef.current = [];
    };
  }, [positions, symbol, candles]);
  return <div className="tt-chart-wrap"><div className="tt-chart-disclaimer">{error ? "MARKET DATA UNAVAILABLE · NO SYNTHETIC FALLBACK" : loading ? "LOADING BIQUOTE MARKET CANDLES…" : `BIQUOTE OHLC · ${interval.toUpperCase()} CANDLES`}</div><div className="tt-chart" ref={host} />{error && <div className="tt-chart-error">{error}</div>}{!error && !loading && !candles.length && <div className="tt-chart-error">No candle data was returned by the provider.</div>}</div>;
}

export default function TradingTerminal() {
  const [symbol, setSymbol] = useState("XAUUSD");
  const [quotes, setQuotes] = useState(EMPTY_QUOTES);
  const [candlesBySymbol, setCandlesBySymbol] = useState({ XAUUSD: [], BTCUSD: [] });
  const [candleErrors, setCandleErrors] = useState({});
  const [feedError, setFeedError] = useState(null);
  const [candleLoading, setCandleLoading] = useState(false);
  const [interval, setInterval] = useState("5m");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyProgress, setHistoryProgress] = useState("");
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [trades, setTrades] = useState([]);
  const [side, setSide] = useState("BUY");
  const [orderType, setOrderType] = useState("MARKET");
  const [quantity, setQuantity] = useState("0.01");
  const [price, setPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [setupType, setSetupType] = useState("Breakout");
  const [strategyName, setStrategyName] = useState("");
  const [entryReason, setEntryReason] = useState("");
  const [emotion, setEmotion] = useState("CALM");
  const [confidence, setConfidence] = useState("7");
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [partialFor, setPartialFor] = useState(null);
  const [partialQty, setPartialQty] = useState("");
  const [protectFor, setProtectFor] = useState(null);
  const [protectSL, setProtectSL] = useState("");
  const [protectTP, setProtectTP] = useState("");
  const [tab, setTab] = useState("positions");
  const quote = quotes[symbol] || EMPTY_QUOTES[symbol];
  const mid = quote.bid != null && quote.ask != null ? (Number(quote.bid) + Number(quote.ask)) / 2 : null;
  const candles = candlesBySymbol[symbol] || [];
  const quoteTime = quote.timestamp ? new Date(quote.timestamp).toLocaleTimeString() : "—";
  const feedLabel = feedError ? "FEED UNAVAILABLE" : quote.stale || quote.market_state === "closed" ? "LAST KNOWN QUOTE" : quote.source === "BIQUOTE" ? "BIQUOTE FEED" : "CONNECTING…";

  const refresh = useCallback(async () => {
    const tasks = await Promise.allSettled([
      client.get("/account"), client.get("/positions"), client.get("/orders?limit=100"), client.get("/trades?limit=200"),
      ...SYMBOLS.map((s) => client.get(`/market/quote?symbol=${s}`)),
    ]);
    if (tasks[0].status === "fulfilled") setAccount(tasks[0].value.data);
    if (tasks[1].status === "fulfilled") setPositions(tasks[1].value.data.positions || []);
    if (tasks[2].status === "fulfilled") setOrders(tasks[2].value.data.orders || []);
    if (tasks[3].status === "fulfilled") setTrades(tasks[3].value.data.trades || []);
    const nextQuotes = { ...EMPTY_QUOTES };
    const failures = [];
    tasks.slice(4).forEach((result, index) => {
      if (result.status === "fulfilled") nextQuotes[SYMBOLS[index]] = result.value.data;
      else failures.push(`${SYMBOLS[index]}: ${result.reason?.response?.data?.detail || result.reason?.message || "quote request failed"}`);
    });
    setQuotes(nextQuotes);
    setFeedError(failures.length ? failures.join(" · ") : null);
  }, []);

  const refreshCandles = useCallback(async (selectedSymbol = symbol, selectedInterval = interval) => {
    setCandleLoading(true);
    try {
      const response = await client.get(`/market/candles?symbol=${selectedSymbol}&interval=${selectedInterval}&limit=200`);
      const bars = (response.data.bars || []).map((bar) => ({
        time: Math.floor(new Date(bar.openTime).getTime() / 1000),
        open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
      })).filter((bar) => Number.isFinite(bar.time) && [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite)).sort((a, b) => a.time - b.time);
      setCandlesBySymbol((previous) => {
        // Merge by candle timestamp so the provider's rolling response does
        // not discard candles already loaded in this browser session.
        const merged = new Map((previous[selectedSymbol] || []).map((bar) => [bar.time, bar]));
        bars.forEach((bar) => merged.set(bar.time, bar));
        return {
          ...previous,
          [selectedSymbol]: Array.from(merged.values()).sort((a, b) => a.time - b.time),
        };
      });
      setCandleErrors((previous) => ({ ...previous, [selectedSymbol]: null }));
    } catch (error) {
      setCandlesBySymbol((previous) => ({ ...previous, [selectedSymbol]: [] }));
      setCandleErrors((previous) => ({ ...previous, [selectedSymbol]: error.response?.data?.detail || error.message || "Candle data unavailable" }));
    } finally { setCandleLoading(false); }
  }, [symbol, interval]);

  const loadOneYear = useCallback(async () => {
    if (historyLoading) return;
    setHistoryLoading(true);
    setHistoryProgress("Preparing historical requests…");
    setCandleErrors((previous) => ({ ...previous, [symbol]: null }));
    const nowMs = Date.now();
    const startMs = nowMs - 365 * 24 * 60 * 60 * 1000;
    const stepMs = INTERVAL_SECONDS[interval] * 1000 * 950; // Stay below the provider's 1,000-bar cap.
    const ranges = [];
    for (let cursor = startMs; cursor < nowMs; cursor += stepMs) {
      ranges.push([cursor, Math.min(cursor + stepMs, nowMs)]);
    }
    let loadedRanges = 0;
    let allBars = [];
    try {
      // Limit concurrency to avoid overwhelming the upstream market-data API.
      for (let i = 0; i < ranges.length; i += 4) {
        const batch = ranges.slice(i, i + 4);
        const results = await Promise.all(batch.map(async ([fromMs, toMs]) => {
          const from = new Date(fromMs).toISOString();
          const to = new Date(toMs).toISOString();
          const response = await client.get("/market/candles", { params: { symbol, interval, limit: 1000, from, to }, timeout: 20000 });
          return (response.data.bars || []).map((bar) => ({
            time: Math.floor(new Date(bar.openTime).getTime() / 1000),
            open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
          })).filter((bar) => Number.isFinite(bar.time) && [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite));
        }));
        allBars.push(...results.flat());
        loadedRanges += batch.length;
        setHistoryProgress(`Loading ${interval} history: ${loadedRanges}/${ranges.length} batches · ${allBars.length.toLocaleString()} candles received`);
      }
      const merged = new Map();
      allBars.sort((a, b) => a.time - b.time).forEach((bar) => merged.set(bar.time, bar));
      setCandlesBySymbol((previous) => {
        const combined = new Map((previous[symbol] || []).map((bar) => [bar.time, bar]));
        merged.forEach((bar, time) => combined.set(time, bar));
        return { ...previous, [symbol]: Array.from(combined.values()).sort((a, b) => a.time - b.time) };
      });
      if (!allBars.length) {
        setCandleErrors((previous) => ({ ...previous, [symbol]: "Biquote returned no candles for the requested one-year range. The provider may not expose that history for this symbol/interval." }));
        setHistoryProgress("No historical candles were returned by the provider.");
      } else {
        const times = allBars.map((bar) => bar.time);
        const first = new Date(times.reduce((min, value) => Math.min(min, value), Infinity) * 1000).toLocaleDateString();
        const last = new Date(times.reduce((max, value) => Math.max(max, value), -Infinity) * 1000).toLocaleDateString();
        setHistoryProgress(`Loaded ${new Set(allBars.map((bar) => bar.time)).size.toLocaleString()} provider candles · ${first} to ${last}. Actual coverage depends on Biquote availability.`);
      }
    } catch (error) {
      setHistoryProgress(`Historical load stopped: ${error.response?.data?.detail || error.message || "request failed"}. Some batches may have loaded.`);
      setCandleErrors((previous) => ({ ...previous, [symbol]: error.response?.data?.detail || error.message || "Historical candle request failed" }));
    } finally { setHistoryLoading(false); }
  }, [historyLoading, symbol, interval]);

  useEffect(() => { refresh(); const timer = window.setInterval(refresh, 5000); return () => window.clearInterval(timer); }, [refresh]);
  useEffect(() => { refreshCandles(symbol, interval); const timer = window.setInterval(() => refreshCandles(symbol, interval), 15000); return () => window.clearInterval(timer); }, [symbol, interval, refreshCandles]);

  useEffect(() => { setPrice(""); setStopLoss(""); setTakeProfit(""); }, [symbol, orderType]);

  const submitOrder = async (event) => {
    event.preventDefault(); setBusy(true); setNotice(null);
    const lastCandle = candles.length ? candles[candles.length - 1] : null;
    const payload = {
      symbol, side, order_type: orderType, quantity: Number(quantity),
      ...(orderType !== "MARKET" && price !== "" ? { price: Number(price) } : {}),
      ...(stopLoss !== "" ? { stop_loss: Number(stopLoss) } : {}),
      ...(takeProfit !== "" ? { take_profit: Number(takeProfit) } : {}),
      setup_type: setupType, strategy_name: strategyName.trim() || null,
      entry_reason: entryReason.trim() || null, emotion, confidence: Number(confidence),
      market_snapshot: {
        captured_at: new Date().toISOString(), source: quote.source || "UNAVAILABLE",
        quote_timestamp: quote.timestamp || null, provider_source: quote.provider_source || null,
        bid: quote.bid ?? null, ask: quote.ask ?? null, market_state: quote.market_state || "unknown",
        stale: Boolean(quote.stale), timeframe: interval,
        latest_candle: lastCandle ? { time: lastCandle.time, open: lastCandle.open, high: lastCandle.high, low: lastCandle.low, close: lastCandle.close } : null,
        recent_closes: candles.slice(-5).map((c) => ({ time: c.time, close: c.close })),
      },
    };
    try {
      const response = await client.post("/orders", payload);
      setNotice({ type: "success", text: `${response.data.status}: ${response.data.message}` });
      await refresh();
    } catch (error) { setNotice({ type: "error", text: error.response?.data?.detail || "Order failed. Check backend connectivity and supported symbols." }); }
    finally { setBusy(false); }
  };

  const closePosition = async (position, partial = false) => {
    const qty = partial ? Number(partialQty) : undefined;
    if (partial && (!Number.isFinite(qty) || qty <= 0 || qty > Number(position.quantity))) {
      setNotice({ type: "error", text: "Enter a valid partial-close quantity not exceeding the open size." }); return;
    }
    setBusy(true); setNotice(null);
    try {
      const response = await client.post(`/positions/${encodeURIComponent(position.position_id)}/close`, partial ? { quantity: qty } : {});
      setNotice({ type: "success", text: `Closed ${num(response.data.closed_quantity, 4)} ${position.symbol}. Realized P&L: ${money(response.data.realized_pnl)}` });
      setPartialFor(null); setPartialQty(""); await refresh();
    } catch (error) { setNotice({ type: "error", text: error.response?.data?.detail || "Could not close position." }); }
    finally { setBusy(false); }
  };

  const saveProtection = async (position) => {
    setBusy(true); setNotice(null);
    try {
      const response = await client.put(`/positions/${encodeURIComponent(position.position_id)}/protection`, {
        stop_loss: protectSL === "" ? null : Number(protectSL),
        take_profit: protectTP === "" ? null : Number(protectTP),
      });
      setNotice({ type: "success", text: `Protection updated for ${position.symbol}. SL/TP are now attached to the demo position.` });
      setProtectFor(null); await refresh();
    } catch (error) { setNotice({ type: "error", text: error.response?.data?.detail || "Could not update SL/TP." }); }
    finally { setBusy(false); }
  };

  const pnlClass = (v) => Number(v) >= 0 ? "positive" : "negative";
  return <div className="tt-page">
    <div className="tt-banner"><div><div className="tt-eyebrow"><Activity size={14}/> DEMO EXECUTION ENVIRONMENT</div><h1>Trading Terminal</h1><p>Practice XAUUSD and BTCUSD with a virtual account. No real orders are sent.</p></div><div className={`tt-sim-pill ${feedError ? "feed-error" : ""}`}><span/> {feedLabel}</div></div>
    {notice && <div className={`tt-notice ${notice.type}`}><span>{notice.type === "success" ? <CheckCircle2 size={17}/> : <AlertCircle size={17}/>} {notice.text}</span><button onClick={() => setNotice(null)} aria-label="Dismiss"><X size={16}/></button></div>}
    <div className="tt-market-strip">
      {SYMBOLS.map((s) => { const q = quotes[s] || EMPTY_QUOTES[s]; return <button key={s} className={`tt-market-chip ${symbol === s ? "selected" : ""}`} onClick={() => setSymbol(s)}><span className="tt-symbol-dot">{s === "XAUUSD" ? "Au" : "₿"}</span><span className="tt-chip-name">{s}<small>{s === "XAUUSD" ? "Gold / US Dollar" : "Bitcoin / US Dollar"}</small></span><strong>{q.bid != null && q.ask != null ? num((Number(q.bid)+Number(q.ask))/2, 2) : "—"}</strong><span className="tt-source">{q.source === "BIQUOTE" ? (q.stale || q.market_state === "closed" ? "STALE" : "LIVE") : "OFF"}</span></button>; })}
    </div>
    <div className="tt-account-grid">
      <div className="tt-stat"><span><Wallet size={16}/> Balance</span><strong>{account ? money(account.balance) : "—"}</strong><small>Virtual USD</small></div>
      <div className="tt-stat"><span><Activity size={16}/> Equity</span><strong>{account ? money(account.equity) : "—"}</strong><small>Balance + unrealized P&L</small></div>
      <div className="tt-stat"><span><ArrowUpRight size={16}/> Total P&L</span><strong className={pnlClass(account?.total_pnl)}>{account ? money(account.total_pnl) : "—"}</strong><small>Realized {account ? money(account.realized_pnl) : "—"} · Open {account ? money(account.unrealized_pnl) : "—"}</small></div>
      <div className="tt-stat"><span><ShieldCheck size={16}/> Open Positions</span><strong>{account?.open_positions ?? positions.length}</strong><small>Across 2 symbols</small></div>
    </div>
    <div className="tt-workspace">
      <section className="tt-panel tt-chart-panel"><div className="tt-panel-head"><div><div className="tt-panel-title">{symbol} <span className="tt-timeframe">{interval}</span></div><div className="tt-quote-line">Bid <b>{quote.bid != null ? num(quote.bid, 2) : "—"}</b><i/> Ask <b>{quote.ask != null ? num(quote.ask, 2) : "—"}</b></div><div className="tt-muted">Updated: {quoteTime}{quote.provider_source ? ` · ${quote.provider_source}` : ""}</div></div><div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap",justifyContent:"flex-end"}}><select aria-label="Candle timeframe" value={interval} onChange={(e)=>{setCandlesBySymbol({XAUUSD:[],BTCUSD:[]});setInterval(e.target.value);setHistoryProgress("");}} style={{background:"#111b2b",color:"#dbeafe",border:"1px solid #2b3b55",borderRadius:7,padding:"7px 9px"}}>{["1m","5m","15m","30m","1h","4h","1d"].map((tf)=><option key={tf} value={tf}>{tf}</option>)}</select><button className="tt-icon-button" onClick={() => loadOneYear()} disabled={historyLoading} title="Load up to one year of provider history">{historyLoading ? "Loading…" : "Load 1Y"}</button><button className="tt-icon-button" onClick={() => { refresh(); refreshCandles(symbol, interval); }} title="Refresh market data"><RefreshCw size={16}/></button></div></div><CandleChart candles={candles} loading={candleLoading} error={candleErrors[symbol]} positions={positions} symbol={symbol} interval={interval}/>{historyProgress && <div style={{padding:"8px 12px",fontSize:12,color:"#9fb1ca",borderTop:"1px solid #243249"}}>{historyProgress}</div>}<div className="tt-chart-foot"><span><Clock3 size={13}/> {quote.stale || quote.market_state === "closed" ? "Last known quote — market may be closed or stale" : "Market data from biquote"}</span><span>Quote source: {quote.source || "UNAVAILABLE"}</span></div></section>
      <section className="tt-panel tt-order-panel"><div className="tt-panel-head"><div><div className="tt-panel-title">Order Ticket</div><div className="tt-muted">{symbol} · {orderType === "MARKET" ? "Instant demo execution" : "Pending order request"}</div></div></div>
        <form onSubmit={submitOrder} className="tt-order-form">
          <label>Instrument<select value={symbol} onChange={(e) => setSymbol(e.target.value)}>{SYMBOLS.map((s) => <option key={s} value={s}>{s} — {s === "XAUUSD" ? "Gold" : "Bitcoin"}</option>)}</select></label>
          <div className="tt-side-switch"><button type="button" className={side === "BUY" ? "buy active" : "buy"} onClick={() => setSide("BUY")}><ArrowUpRight size={16}/> Buy</button><button type="button" className={side === "SELL" ? "sell active" : "sell"} onClick={() => setSide("SELL")}><ArrowDownRight size={16}/> Sell</button></div>
          <label>Order type<select value={orderType} onChange={(e) => setOrderType(e.target.value)}><option value="MARKET">Market</option><option value="LIMIT">Limit (stored only)</option><option value="STOP">Stop (stored only)</option></select></label>
          <label>Quantity<input type="number" min="0.0001" max="100" step="any" required value={quantity} onChange={(e) => setQuantity(e.target.value)}/><small>Simulator units; contract sizing is simplified.</small></label>
          <div className="tt-context-box">
            <div className="tt-context-title">Journal this entry</div>
            <label>Setup type<select value={setupType} onChange={(e) => setSetupType(e.target.value)}><option>Breakout</option><option>Pullback</option><option>Trend continuation</option><option>Mean reversion</option><option>Support / resistance</option><option>News / event</option><option>Scalp</option><option>Other</option></select></label>
            <label>Entry thesis / reason<textarea rows={2} maxLength={1000} value={entryReason} onChange={(e) => setEntryReason(e.target.value)} placeholder="What is the setup trigger? What invalidates it?"/></label>
            <label>Strategy name (optional)<input maxLength={100} value={strategyName} onChange={(e) => setStrategyName(e.target.value)} placeholder="e.g. VWAP pullback"/></label>
            <div className="tt-two-inputs"><label>Entry emotion<select value={emotion} onChange={(e) => setEmotion(e.target.value)}><option value="CALM">Calm / disciplined</option><option value="CONFIDENT">Confident</option><option value="FOMO">FOMO</option><option value="REVENGE">Revenge</option><option value="FRUSTRATED">Frustrated</option><option value="ANXIOUS">Anxious</option><option value="FEARFUL">Fearful</option><option value="TIRED">Tired</option></select></label><label>Confidence (1–10)<select value={confidence} onChange={(e) => setConfidence(e.target.value)}>{Array.from({length:10}, (_,i) => i+1).map((n) => <option key={n} value={n}>{n}/10</option>)}</select></label></div>
            <small>These details are saved with the entry and copied into the journal after exit.</small>
          </div>
          {orderType !== "MARKET" && <label>Trigger price<input type="number" min="0.000001" step="any" required value={price} onChange={(e) => setPrice(e.target.value)} placeholder={mid != null ? `Current ~ ${num(mid, 2)}` : "Quote unavailable"}/><small>Pending triggers are not monitored yet.</small></label>}
          <div className="tt-two-inputs"><label>Stop loss <input type="number" min="0.000001" step="any" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} placeholder="Optional"/></label><label>Take profit<input type="number" min="0.000001" step="any" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)} placeholder="Optional"/></label></div>
          <div className="tt-estimate"><span>Indicative price</span><strong>{(side === "BUY" ? quote.ask : quote.bid) != null ? num(side === "BUY" ? quote.ask : quote.bid, 2) : "Unavailable"}</strong></div>
          <button className={`tt-submit ${side.toLowerCase()}`} disabled={busy} type="submit">{busy ? "Processing…" : `${side} ${symbol}`}</button>
          <div className="tt-risk-note"><AlertCircle size={14}/> Demo only. SL/TP lines are drawn on the chart and execute in the simulator when a fresh quote crosses them.</div>
        </form>
      </section>
    </div>
    <section className="tt-panel tt-book-panel"><div className="tt-book-head"><div><div className="tt-panel-title">Trade Book</div><div className="tt-muted">Manage simulated exposure and review closes</div></div><div className="tt-tabs">{[["positions",`Open Positions (${positions.length})`],["orders",`Orders (${orders.length})`],["history",`History (${trades.length})`]].map(([id,label]) => <button key={id} className={tab===id?"active":""} onClick={() => setTab(id)}>{label}</button>)}</div></div>
      {tab === "positions" ? (positions.length ? <div className="tt-table-wrap"><table className="tt-table"><thead><tr><th>SYMBOL</th><th>SIDE</th><th>SIZE</th><th>ENTRY</th><th>MARK</th><th>SL / TP</th><th>UNREALIZED P&L</th><th>ACTIONS</th></tr></thead><tbody>{positions.map((p) => <tr key={p.position_id}><td><strong>{p.symbol}</strong><small>{p.position_id}</small></td><td><span className={`tt-side-tag ${p.side.toLowerCase()}`}>{p.side}</span></td><td>{num(p.quantity, 4)}</td><td>{num(p.entry_price, 2)}</td><td>{p.mark_price != null ? num(p.mark_price, 2) : "—"}</td><td>{p.stop_loss ? num(p.stop_loss,2) : "—"} / {p.take_profit ? num(p.take_profit,2) : "—"}</td><td className={pnlClass(p.unrealized_pnl)}>{p.unrealized_pnl != null ? money(p.unrealized_pnl) : "—"}</td><td><div className="tt-actions">{protectFor === p.position_id ? <div className="tt-protect-editor"><label>SL <input type="number" min="0.000001" step="any" value={protectSL} onChange={(e)=>setProtectSL(e.target.value)} placeholder="Off"/></label><label>TP <input type="number" min="0.000001" step="any" value={protectTP} onChange={(e)=>setProtectTP(e.target.value)} placeholder="Off"/></label><button disabled={busy} onClick={()=>saveProtection(p)}>Save</button><button className="ghost" onClick={()=>setProtectFor(null)}>Cancel</button></div> : partialFor === p.position_id ? <><input className="tt-partial-input" type="number" min="0.0001" max={p.quantity} step="any" value={partialQty} onChange={(e)=>setPartialQty(e.target.value)} placeholder="Qty"/><button disabled={busy} onClick={()=>closePosition(p,true)}>Close qty</button><button className="ghost" onClick={()=>setPartialFor(null)}>Cancel</button></> : <><button onClick={()=>{setProtectFor(p.position_id);setProtectSL(p.stop_loss ?? "");setProtectTP(p.take_profit ?? "")}}>Protect / SL-TP</button><button onClick={()=>{setPartialFor(p.position_id);setPartialQty("")}}>Partial</button><button className="danger" disabled={busy} onClick={()=>closePosition(p,false)}>Close all</button></>}</div></td></tr>)}</tbody></table></div> : <div className="tt-empty">No open positions. Place a demo market order to get started.</div>) : tab === "orders" ? (orders.length ? <div className="tt-table-wrap"><table className="tt-table"><thead><tr><th>ORDER ID</th><th>SYMBOL</th><th>SIDE</th><th>TYPE</th><th>QTY</th><th>TRIGGER</th><th>STATUS</th><th>CREATED</th></tr></thead><tbody>{orders.map((o)=><tr key={o.order_id}><td>{o.order_id}</td><td>{o.symbol}</td><td>{o.side}</td><td>{o.order_type}</td><td>{num(o.quantity,4)}</td><td>{o.requested_price ? num(o.requested_price,2) : "—"}</td><td><span className="tt-status">{o.status}</span></td><td>{o.created_at ? new Date(o.created_at).toLocaleString() : "—"}</td></tr>)}</tbody></table></div> : <div className="tt-empty">No orders recorded yet.</div>) : (trades.length ? <div className="tt-table-wrap"><table className="tt-table"><thead><tr><th>TRADE ID</th><th>SYMBOL</th><th>SIDE</th><th>QTY CLOSED</th><th>ENTRY</th><th>EXIT</th><th>REALIZED P&L</th><th>CLOSED AT</th></tr></thead><tbody>{trades.map((t)=><tr key={t.trade_id}><td>{t.trade_id}</td><td>{t.symbol}</td><td>{t.side}</td><td>{num(t.quantity,4)}</td><td>{num(t.entry_price,2)}</td><td>{num(t.exit_price,2)}</td><td className={pnlClass(t.realized_pnl)}>{money(t.realized_pnl)}</td><td>{t.closed_at ? new Date(t.closed_at).toLocaleString() : "—"}</td></tr>)}</tbody></table></div> : <div className="tt-empty">Closed trades will appear here.</div>)}
    </section>
    <p className="tt-footer-note">Market quotes and candles are requested from the third-party biquote API; freshness depends on that provider and the market session. This remains a DEMO-ONLY simulator and does not send broker orders. If the feed is unavailable, the chart stays empty rather than fabricating candles. Pending orders do not trigger automatically. Stop-loss/take-profit execution is checked against fresh quotes while the simulator endpoints are being refreshed.</p>
  </div>;
}
