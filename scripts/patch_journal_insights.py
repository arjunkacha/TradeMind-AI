from pathlib import Path
import re, sys
path = Path("frontend/src/App.jsx")
if not path.exists():
    print("ERROR: Run this script from your TradeMind-AI project root.")
    sys.exit(1)
s = path.read_text(encoding="utf-8")
if "function SimulatorJournalInsights()" not in s:
    component = r'''

function SimulatorJournalInsights() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    api.get("/api/simulator/journal/insights?limit=100")
      .then((r) => { if (!cancelled) setData(r?.data || null); })
      .catch((e) => { if (!cancelled) setError(e?.response?.data?.detail || "Simulator insights unavailable"); });
    return () => { cancelled = true; };
  }, []);
  const summary = data?.summary || {};
  return (
    <section style={{ border: "1px solid #263247", borderRadius: "14px", background: "#0b1220", padding: "16px", marginBottom: "16px" }}>
      <div className="eyebrow">PERSONALIZED SIMULATOR INSIGHTS</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: "10px", marginTop: "12px" }}>
        {[["Closed trades", summary.trades ?? 0], ["Win rate", `${summary.win_rate ?? 0}%`], ["Net P&L", `${Number(summary.net_pnl ?? 0) >= 0 ? "+" : ""}${Number(summary.net_pnl ?? 0).toFixed(2)} USD`], ["Average R", summary.average_r == null ? "—" : `${Number(summary.average_r).toFixed(2)}R`]].map(([label,value]) => (
          <div key={label} style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "9px", padding: "11px" }}><div style={{ color: "#64748b", fontSize: "10px", textTransform: "uppercase" }}>{label}</div><strong style={{ display: "block", color: "#e2e8f0", marginTop: "5px" }}>{value}</strong></div>
        ))}
      </div>
      {error ? <p style={{ color: "#fca5a5", fontSize: "12px" }}>{error}</p> : <ul style={{ color: "#cbd5e1", fontSize: "12px", lineHeight: 1.7, paddingLeft: "18px", marginBottom: 0 }}>{(data?.insights || ["Close demo trades and record entry context to build insights."]).map((x,i) => <li key={i}>{x}</li>)}</ul>}
      <div style={{ color: "#818cf8", fontSize: "10px", marginTop: "10px" }}>Descriptive rules over your recorded trades — not a predictive ML signal.</div>
    </section>
  );
}
'''
    marker = "function TradeJournalDetail({ trade, onClose }) {"
    if marker not in s:
        print("ERROR: Could not locate TradeJournalDetail in App.jsx. No changes made.")
        sys.exit(2)
    s = s.replace(marker, component + "\n" + marker, 1)
# Add insights panel once in TradeJournalPage before its main journal Panel.
if "<SimulatorJournalInsights />" not in s:
    start = s.find("function TradeJournalPage(")
    if start < 0:
        print("ERROR: Could not locate TradeJournalPage in App.jsx. No changes made.")
        sys.exit(3)
    end = s.find("function TradeJournalDetail(", start)
    chunk = s[start:end if end >= 0 else len(s)]
    panel = re.search(r"\n(\s*)<Panel\n", chunk)
    if not panel:
        print("ERROR: Could not locate journal Panel. No changes made.")
        sys.exit(4)
    pos = start + panel.start()
    s = s[:pos] + "\n        <SimulatorJournalInsights />\n" + s[pos:]
# Extend selected simulator journal details; only insert if missing.
needle = '    ["P&L", formatMoney(detail.net_pnl ?? detail.pnl ?? detail.profit ?? detail.realized_pnl)],'
if needle in s and '["Entry Thesis", detail.entry_reason]' not in s:
    s = s.replace(needle, needle + '\n    ["Setup", detail.setup_type],\n    ["Strategy", detail.strategy_name],\n    ["Entry Thesis", detail.entry_reason],\n    ["Entry Emotion", detail.emotion],\n    ["Entry Confidence", detail.confidence != null ? `${detail.confidence}/10` : "—"],\n    ["Exit Reason", detail.close_reason],\n    ["R Multiple", detail.r_multiple != null ? `${detail.r_multiple}R` : "—"],', 1)
# Show market snapshot in detail, using JSON text so no chart data is hidden.
needle = '      <div style={{ padding: "0 16px 16px" }}>\n        <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>\n          Detected Behaviors'
if needle in s and 'Entry Market Snapshot' not in s:
    block = '''      {detail.source === "simulator_auto" && detail.market_snapshot && (
        <div style={{ padding: "0 16px 16px" }}>
          <div style={{ border: "1px solid #1e293b", borderRadius: "10px", padding: "12px", background: "#0f172a" }}>
            <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>Entry Market Snapshot</div>
            <div style={{ color: "#cbd5e1", fontSize: "12px", lineHeight: 1.7 }}>
              Source: {detail.market_snapshot.provider_source || detail.market_snapshot.source || "—"} · Bid: {detail.market_snapshot.bid ?? "—"} · Ask: {detail.market_snapshot.ask ?? "—"} · State: {detail.market_snapshot.market_state || "—"}
              {detail.market_snapshot.latest_candle && <div>Last 5m candle O/H/L/C: {detail.market_snapshot.latest_candle.open} / {detail.market_snapshot.latest_candle.high} / {detail.market_snapshot.latest_candle.low} / {detail.market_snapshot.latest_candle.close}</div>}
            </div>
          </div>
        </div>
      )}

'''
    s = s.replace(needle, block + needle, 1)
path.write_text(s, encoding="utf-8")
print("Patched App.jsx with simulator journal insights and entry-context details.")
