from pathlib import Path
import re
import sys

path = Path("frontend/src/App.jsx")
if not path.exists():
    print("ERROR: Run this script from your TradeMind-AI project root (the folder containing frontend/ and backend/).")
    sys.exit(1)

text = path.read_text(encoding="utf-8")
if "const loadJournal = async () => {" not in text:
    print("ERROR: Could not find loadJournal in App.jsx. No file was changed.")
    sys.exit(2)

pattern = re.compile(
    r"  const loadJournal = async \(\) => \{.*?\n  \};\n\n  const handleTradingViewImport = async \(\) => \{",
    re.S,
)
replacement = r'''  const loadJournal = async () => {
    try {
      setJournalLoading(true);
      // Combine auto-journal entries created by the simulator on exit with
      // the existing imported TradingView AI journal.
      const [simResult, importedResult] = await Promise.allSettled([
        api.get("/api/simulator/journal?limit=200"),
        (async () => {
          try {
            return await api.get("/api/tradingview/trades?limit=200");
          } catch {
            return await api.get("/api/tradingview/ml-predictions");
          }
        })(),
      ]);

      const simulatorEntries =
        simResult.status === "fulfilled"
          ? (simResult.value?.data?.journal || []).map((entry) => ({
              ...entry,
              source: "simulator_auto",
              direction: entry.direction || entry.side,
              net_pnl: entry.net_pnl ?? entry.realized_pnl,
              exit_time: entry.exit_time || entry.closed_at,
              entry_time: entry.entry_time || entry.opened_at,
              behaviors: entry.behaviors || "",
            }))
          : [];

      const importedEntries =
        importedResult.status === "fulfilled"
          ? normalizeList(importedResult.value).map((entry) => ({
              ...entry,
              source: entry.source || "tradingview_import",
            }))
          : [];

      const combined = [...simulatorEntries, ...importedEntries];
      combined.sort((a, b) => {
        const aTime = Date.parse(a.closed_at || a.exit_time || a.timestamp || "") || 0;
        const bTime = Date.parse(b.closed_at || b.exit_time || b.timestamp || "") || 0;
        return bTime - aTime;
      });
      setJournalTrades(combined);
    } catch (err) {
      console.error("Journal load error:", err);
      setJournalTrades([]);
    } finally {
      setJournalLoading(false);
    }
  };

  const handleTradingViewImport = async () => {'''
text2, n = pattern.subn(lambda m: replacement, text, count=1)
if n != 1:
    print("ERROR: Could not safely patch loadJournal. No file was changed.")
    sys.exit(3)
text = text2

text = text.replace(
    "Review imported TradingView Paper trades together with TradeMind\n            behavior, risk, ML and decision signals.",
    "Review automatically journaled simulator exits alongside imported TradingView trades and their TradeMind analysis."
)
text = text.replace(
    'description="Imported TradingView records"',
    'description="Auto exits + imported records"'
)
text = text.replace(
    'title="TradingView Paper Journal"',
    'title="Automatic + Imported Trade Journal"'
)
text = text.replace(
    'subtitle="Trade-level records produced by the TradeMind analysis pipeline"',
    'subtitle="Closed simulator trades are journaled automatically; TradingView imports retain their AI analysis."'
)
text = text.replace(
    'No journal trades found. Import a TradingView Paper CSV to begin.',
    'No closed simulator trades or imported journal records yet. Close a demo trade to create an automatic journal entry.'
)

needle = '''    const tradeId = trade?.trade_id || trade?.id;
    if (!tradeId) return;

    let cancelled = false;
'''
replacement = '''    const tradeId = trade?.trade_id || trade?.id;
    if (!tradeId) return;
    if (trade?.source === "simulator_auto" || String(tradeId).startsWith("SIM-TRD-")) {
      setDetail(trade || {});
      setLoadingDetail(false);
      return;
    }

    let cancelled = false;
'''
if needle in text:
    text = text.replace(needle, replacement, 1)
else:
    print("WARNING: Could not add simulator detail guard; journal list patch was applied.")

needle = '''    ["P&L", formatMoney(detail.net_pnl ?? detail.pnl ?? detail.profit ?? detail.realized_pnl)],
    ["Holding Time", detail.holding_minutes != null ? `${detail.holding_minutes} min` : "—"],
'''
replacement = '''    ["P&L", formatMoney(detail.net_pnl ?? detail.pnl ?? detail.profit ?? detail.realized_pnl)],
    ["Exit Reason", detail.close_reason],
    ["R Multiple", detail.r_multiple != null ? `${detail.r_multiple}R` : "—"],
    ["Holding Time", detail.holding_minutes != null ? `${detail.holding_minutes} min` : "—"],
'''
if needle in text:
    text = text.replace(needle, replacement, 1)

needle = '''      <div style={{ padding: "0 16px 16px" }}>
        <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>
          Detected Behaviors
'''
replacement = '''      {detail.source === "simulator_auto" && (
        <div style={{ padding: "0 16px 16px" }}>
          <div style={{ border: "1px solid #3b2f68", borderRadius: "10px", padding: "14px", background: "#111027" }}>
            <div style={{ color: "#c4b5fd", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>
              Automatic Trade Review
            </div>
            <p style={{ color: "#e2e8f0", fontSize: "13px", lineHeight: 1.6, margin: "0 0 10px" }}>
              {detail.ai_summary || "Review generated from recorded entry, exit, P&L and protection levels."}
            </p>
            {Array.isArray(detail.lessons) && detail.lessons.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: "18px", color: "#cbd5e1", fontSize: "12px", lineHeight: 1.7 }}>
                {detail.lessons.map((lesson, index) => <li key={index}>{lesson}</li>)}
              </ul>
            )}
            <div style={{ color: "#818cf8", fontSize: "10px", marginTop: "10px" }}>
              Execution-based coaching - not an ML prediction
            </div>
          </div>
        </div>
      )}

      <div style={{ padding: "0 16px 16px" }}>
        <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>
          Detected Behaviors
'''
if needle in text:
    text = text.replace(needle, replacement, 1)
else:
    print("WARNING: Could not insert review panel; core auto-journal list integration was applied.")

path.write_text(text, encoding="utf-8")
print("Patched frontend/src/App.jsx to combine automatic simulator journal entries with imported TradingView journal records.")
