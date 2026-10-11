import TradeAnalysis from "./components/TradeAnalysis";
import TradingTerminal from "./components/TradingTerminal";
import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  Activity,
  AlertTriangle,
  BookOpen,
  Upload,
  Search,
  CheckCircle2,
  BrainCircuit,
  ChevronRight,
  CircleDollarSign,
  Gauge,
  LayoutDashboard,
  Menu,
  RefreshCw,
  ShieldAlert,
  Target,
  TrendingUp,
  UserRound,
  X,
  Zap,
} from "lucide-react";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import "./index.css";

const API = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API,
  timeout: 10000,
});

const decisionColors = {
  ALLOW: "#22c55e",
  CAUTION: "#f59e0b",
  "AVOID / REDUCE RISK": "#f97316",
  "DO NOT TRADE": "#ef4444",
};

const riskColors = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

function formatPercent(value) {
  if (value === undefined || value === null) return "—";

  const number = Number(value);

  if (Number.isNaN(number)) return "—";

  return `${(number <= 1 ? number * 100 : number).toFixed(2)}%`;
}

function formatNumber(value) {
  if (value === undefined || value === null) return "—";

  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}

function normalizeList(response) {
  if (Array.isArray(response?.data)) return response.data;

  if (Array.isArray(response?.data?.data)) {
    return response.data.data;
  }

  if (Array.isArray(response?.data?.trades)) {
    return response.data.trades;
  }

  if (Array.isArray(response?.data?.traders)) {
    return response.data.traders;
  }

  if (Array.isArray(response?.data?.predictions)) {
    return response.data.predictions;
  }

  if (Array.isArray(response?.data?.events)) {
    return response.data.events;
  }

  return [];
}

function App() {
  const [dashboard, setDashboard] = useState(null);

  // --------------------------------------------------
  // DATA SOURCE
  // --------------------------------------------------
  const [dataSource, setDataSource] = useState("simulator");
  const [mlMetrics, setMlMetrics] = useState(null);
  const [highRiskTrades, setHighRiskTrades] = useState([]);
  const [behaviors, setBehaviors] = useState([]);
  const [traderProfiles, setTraderProfiles] = useState([]);
  const [mlPredictions, setMlPredictions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // --------------------------------------------------
  // PAGE NAVIGATION
  // --------------------------------------------------
  const [activePage, setActivePage] = useState("dashboard");

  // --------------------------------------------------
  // TRADE JOURNAL / TRADINGVIEW IMPORT
  // --------------------------------------------------
  const [journalTrades, setJournalTrades] = useState([]);
  const [journalLoading, setJournalLoading] = useState(false);
  const [journalSearch, setJournalSearch] = useState("");
  const [selectedJournalTrade, setSelectedJournalTrade] = useState(null);
  const [showImport, setShowImport] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState(null);

  const loadJournal = async (source = dataSource) => {
    try {
      setJournalLoading(true);
      // Combine auto-journal entries created by the simulator on exit with
      // the existing imported TradingView AI journal.
      const [simResult, importedResult] = await Promise.allSettled([
        api.get("/api/simulator/journal?limit=500"),
        source === "tradingview"
          ? (async () => {
              try {
                return await api.get("/api/tradingview/trades?limit=200");
              } catch {
                return await api.get("/api/tradingview/ml-predictions");
              }
            })()
          : Promise.resolve({ data: { trades: [] } }),
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

  const handleTradingViewImport = async () => {
    if (!importFile) return;

    try {
      setImporting(true);
      setImportStatus(null);

      const formData = new FormData();
      formData.append("file", importFile);

      const response = await api.post(
        "/api/tradingview/import?account=TradingView-Paper",
        formData,
        { headers: { "Content-Type": "multipart/form-data" }, timeout: 120000 }
      );

      setImportStatus({
        type: "success",
        message: `Imported ${formatNumber(response.data?.completed_trades || 0)} trades and ran the TradeMind AI pipeline.`
      });

      setImportFile(null);
      await loadDashboard("tradingview");
      await loadJournal("tradingview");
      setDataSource("tradingview");
      return true;
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        "TradingView import failed. Check the FastAPI terminal for details.";
      setImportStatus({ type: "error", message: detail });
      return false;
    } finally {
      setImporting(false);
    }
  };

  const loadDashboard = async (source = dataSource) => {
    try {
      setRefreshing(true);
      setError(null);

      // Default mode is based only on closed demo-simulator journal entries.
      // The historical CSV-backed endpoints are called only when the user
      // explicitly switches to the optional TradingView import analysis.
      if (source === "simulator") {
        const response = await api.get("/api/simulator/journal?limit=500");
        const journal = Array.isArray(response.data?.journal)
          ? response.data.journal
          : [];

        const asNumber = (value) => {
          const number = Number(value);
          return Number.isFinite(number) ? number : 0;
        };
        const pnlOf = (trade) =>
          asNumber(trade.realized_pnl ?? trade.net_pnl ?? trade.pnl);
        const closedTrades = journal.filter((trade) =>
          trade.closed_at || trade.exit_time
        );
        // Keep the simulator's real journal rows available to every page,
        // not only when the Journal navigation item is opened.
        setJournalTrades(closedTrades.map((trade) => ({
          ...trade,
          source: "simulator_auto",
          direction: trade.direction || trade.side,
          net_pnl: trade.net_pnl ?? trade.realized_pnl ?? trade.pnl,
          entry_time: trade.entry_time || trade.opened_at,
          exit_time: trade.exit_time || trade.closed_at,
        })));
        const decisions = {};
        const risks = {};
        const behaviorCounts = {};
        closedTrades.forEach((trade) => {
          const decision = trade.decision || "REVIEW";
          decisions[decision] = (decisions[decision] || 0) + 1;
          const risk = String(trade.risk_level || "UNKNOWN").toUpperCase();
          risks[risk] = (risks[risk] || 0) + 1;
          let flags = trade.behaviors;
          if (typeof flags === "string") {
            try {
              flags = JSON.parse(flags);
            } catch {
              flags = flags ? flags.split(",").map((value) => value.trim()).filter(Boolean) : [];
            }
          }
          if (!Array.isArray(flags)) flags = [];
          flags.forEach((flag) => {
            const name = typeof flag === "string" ? flag : flag?.behavior;
            if (name) behaviorCounts[name] = (behaviorCounts[name] || 0) + 1;
          });
          if (!flags.length && trade.close_reason) {
            const name = trade.close_reason === "STOP_LOSS"
              ? "Stop-Loss Exit"
              : trade.close_reason === "TAKE_PROFIT"
              ? "Take-Profit Exit"
              : null;
            if (name) behaviorCounts[name] = (behaviorCounts[name] || 0) + 1;
          }
        });

        const riskScores = closedTrades
          .map((trade) => Number(trade.risk_score))
          .filter(Number.isFinite);
        const rValues = closedTrades
          .map((trade) => Number(trade.r_multiple ?? trade.r_multiple_value))
          .filter(Number.isFinite);

        setDashboard({
          total_trades: closedTrades.length,
          average_risk_score: riskScores.length
            ? riskScores.reduce((sum, value) => sum + value, 0) / riskScores.length
            : null,
          average_discipline_score: null,
          average_ml_win_probability: null,
          decision_distribution: decisions,
          risk_distribution: risks,
          realized_pnl: closedTrades.reduce((sum, trade) => sum + pnlOf(trade), 0),
          wins: closedTrades.filter((trade) => pnlOf(trade) > 0).length,
          losses: closedTrades.filter((trade) => pnlOf(trade) < 0).length,
          win_rate: closedTrades.length
            ? (closedTrades.filter((trade) => pnlOf(trade) > 0).length / closedTrades.length) * 100
            : 0,
          average_r_multiple: rValues.length
            ? rValues.reduce((sum, value) => sum + value, 0) / rValues.length
            : null,
        });
        setMlMetrics(null);
        setHighRiskTrades(closedTrades
          .filter((trade) => ["HIGH", "CRITICAL"].includes(String(trade.risk_level || "").toUpperCase()))
          .map((trade) => ({
            ...trade,
            trade_id: trade.trade_id || trade.id,
            account: trade.account || "Demo Simulator",
            decision: trade.decision || "REVIEW",
          })));
        const avgRisk = riskScores.length
          ? riskScores.reduce((sum, value) => sum + value, 0) / riskScores.length
          : null;
        setTraderProfiles([{
          account: "Demo Simulator",
          total_trades: closedTrades.length,
          trade_count: closedTrades.length,
          average_risk_score: avgRisk,
          discipline_score: null,
          behavior_score: Object.values(behaviorCounts).reduce((sum, value) => sum + value, 0),
          win_rate: closedTrades.length
            ? (closedTrades.filter((trade) => pnlOf(trade) > 0).length / closedTrades.length) * 100
            : 0,
          profile_note: "Derived from the simulator's recorded closed trades; no profile-level ML score is inferred.",
        }]);
        setBehaviors(Object.entries(behaviorCounts).map(([behavior, value]) => ({ behavior, value })));
        // Do not fabricate ML predictions for simulator trades. The ML page
        // will show a transparent unavailable state until a model endpoint is connected.
        setMlPredictions([]);
        return;
      }

      const [
        dashboardResponse,
        mlResponse,
        riskResponse,
        behaviorResponse,
        profileResponse,
      ] = await Promise.all([
        api.get("/api/tradingview/dashboard"),
        api.get("/api/ml-metrics"),
        api.get("/api/tradingview/high-risk-trades"),
        api.get("/api/tradingview/behaviors"),
        api.get("/api/tradingview/traders"),
      ]);

      setDashboard(dashboardResponse.data);
      setMlMetrics(mlResponse.data);
      const riskList = normalizeList(riskResponse);
      setHighRiskTrades(riskList);
      setTraderProfiles(normalizeList(profileResponse));

      const behaviorPayload = behaviorResponse.data || {};
      const behaviorCounts = behaviorPayload.behaviors || {};
      setBehaviors(Object.entries(behaviorCounts).map(([behavior, value]) => ({
        behavior,
        value: Number(value) || 0,
      })));

      try {
        const predictionResponse = await api.get("/api/tradingview/ml-predictions");
        setMlPredictions(normalizeList(predictionResponse));
      } catch (predictionError) {
        console.warn("TradingView ML predictions unavailable:", predictionError);
        setMlPredictions(riskList);
      }
    } catch (err) {
      console.error("TradeMind API error:", err);
      setError(
        source === "simulator"
          ? "Unable to load demo trading journal. Make sure FastAPI is running and the simulator router is registered."
          : "No TradingView analysis is available yet. Import a TradingView CSV first."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboard("simulator");
  }, []);

  useEffect(() => {
    loadDashboard(dataSource);
  }, [dataSource]);

  useEffect(() => {
    if (activePage === "journal") {
      loadJournal(dataSource);
    }
  }, [activePage, dataSource]);

  const decisionData = useMemo(() => {
    if (!dashboard?.decision_distribution) return [];

    return Object.entries(dashboard.decision_distribution).map(
      ([name, value]) => ({
        name,
        value,
      })
    );
  }, [dashboard]);

  const riskData = useMemo(() => {
    if (!dashboard?.risk_distribution) return [];

    return Object.entries(dashboard.risk_distribution).map(
      ([name, value]) => ({
        name,
        value,
      })
    );
  }, [dashboard]);

  const behaviorData = useMemo(() => {
    if (!behaviors?.length) return [];

    const counts = {};

    behaviors.forEach((item) => {
      const behavior =
        item.behavior ||
        item.name ||
        item.behavior_type;

      if (!behavior) return;

      counts[behavior] = (counts[behavior] || 0) + 1;
    });

    return Object.entries(counts)
      .map(([name, value]) => ({
        name,
        value,
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
  }, [behaviors]);

  const ml = mlMetrics?.metrics || {};

  // --------------------------------------------------
  // LOADING SCREEN
  // --------------------------------------------------
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-logo">
          <BrainCircuit size={34} />
        </div>

        <h1>TradeMind AI</h1>

        <div className="loading-line">
          <span />
        </div>

        <p>Loading trading intelligence...</p>
      </div>
    );
  }

  // --------------------------------------------------
  // ERROR SCREEN
  // --------------------------------------------------
  if (error && !dashboard) {
    return (
      <div className="error-screen">
        <ShieldAlert size={52} />

        <h1>TradeMind AI</h1>

        <p>{error}</p>

        <button
          className="primary-button"
          onClick={loadDashboard}
        >
          <RefreshCw size={17} />
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="app-shell">

      {/* ==================================================
          MOBILE OVERLAY
      ================================================== */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ==================================================
          SIDEBAR
      ================================================== */}
      <aside
        className={`sidebar ${
          sidebarOpen ? "open" : ""
        }`}
      >
        {/* BRAND */}
        <div className="brand">
          <div className="brand-icon">
            <BrainCircuit size={24} />
          </div>

          <div>
            <div className="brand-name">
              TradeMind
            </div>

            <div className="brand-subtitle">
              AI INTELLIGENCE
            </div>
          </div>

          <button
            className="mobile-close"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* NAVIGATION */}
        <nav className="sidebar-nav">

          <div className="nav-section">
            MAIN
          </div>

          {/* DASHBOARD */}
          <button
            className={`nav-item ${
              activePage === "dashboard"
                ? "active"
                : ""
            }`}
            onClick={() => {
              setActivePage("dashboard");
              setSidebarOpen(false);
            }}
          >
            <LayoutDashboard size={18} />
            Dashboard
          </button>

          {/* TRADE ANALYSIS */}
          <button
            className={`nav-item ${
              activePage === "trade-analysis"
                ? "active"
                : ""
            }`}
            onClick={() => {
              setActivePage("trade-analysis");
              setSidebarOpen(false);
            }}
          >
            <Activity size={18} />
            Trade Analysis
          </button>

          {/* TRADE JOURNAL */}
          <button
            className={`nav-item ${
              activePage === "journal" ? "active" : ""
            }`}
            onClick={() => {
              setActivePage("journal");
              setSidebarOpen(false);
            }}
          >
            <BookOpen size={18} />
            Trade Journal
          </button>

          {/* TRADER PROFILES */}
          <button
            className={`nav-item ${
              activePage === "trader-profiles" ? "active" : ""
            }`}
            onClick={() => {
              setActivePage("trader-profiles");
              setSidebarOpen(false);
            }}
          >
            <UserRound size={18} />
            Trader Profiles
          </button>

          {/* DEMO TRADING TERMINAL */}
          <button
            className={`nav-item ${activePage === "trading-terminal" ? "active" : ""}`}
            onClick={() => {
              setActivePage("trading-terminal");
              setSidebarOpen(false);
            }}
          >
            <TrendingUp size={18} />
            Trading Terminal
          </button>

          <div className="nav-section">
            INTELLIGENCE
          </div>

          {/* RISK INTELLIGENCE */}
          <button
            className={`nav-item ${
              activePage === "risk-intelligence" ? "active" : ""
            }`}
            onClick={() => {
              setActivePage("risk-intelligence");
              setSidebarOpen(false);
            }}
          >
            <ShieldAlert size={18} />
            Risk Intelligence
          </button>

          {/* BEHAVIORAL AI */}
          <button
            className={`nav-item ${
              activePage === "behavioral-ai" ? "active" : ""
            }`}
            onClick={() => {
              setActivePage("behavioral-ai");
              setSidebarOpen(false);
            }}
          >
            <BrainCircuit size={18} />
            Behavioral AI
          </button>

          {/* ML PREDICTIONS */}
          <button
            className={`nav-item ${
              activePage === "ml-predictions" ? "active" : ""
            }`}
            onClick={() => {
              setActivePage("ml-predictions");
              setSidebarOpen(false);
            }}
          >
            <Target size={18} />
            ML Predictions
          </button>
        </nav>

        {/* SIDEBAR BOTTOM */}
        <div className="sidebar-bottom">

          <div className="system-status">
            <span className="status-dot" />

            <div>
              <strong>
                System Online
              </strong>

              <small>
                FastAPI connected
              </small>
            </div>
          </div>

          <div className="version">
            TradeMind AI v1.0
          </div>

        </div>
      </aside>

      {/* ==================================================
          MAIN
      ================================================== */}
      <main className="main-content">

        {/* TOPBAR */}
        <header className="topbar">

          <button
            className="menu-button"
            onClick={() =>
              setSidebarOpen(true)
            }
          >
            <Menu size={22} />
          </button>

          <div>
            <div className="page-title">
              {activePage === "trading-terminal"
                ? "Trading Terminal"
                : activePage === "trade-analysis"
                ? "Trade Analysis"
                : activePage === "trader-profiles"
                ? "Trader Profiles"
                : activePage === "risk-intelligence"
                ? "Risk Intelligence"
                : activePage === "behavioral-ai"
                ? "Behavioral AI"
                : activePage === "ml-predictions"
                ? "ML Predictions"
                : "Trading Intelligence"}
            </div>

            <div className="page-subtitle">
              {activePage === "trading-terminal"
                ? "XAUUSD and BTCUSD demo trading workspace"
                : activePage === "trade-analysis"
                ? "Detailed trade-level behavioral analysis"
                : activePage === "trader-profiles"
                ? "Account-level trader behavioral intelligence"
                : activePage === "risk-intelligence"
                ? "Portfolio and trade-level behavioral risk analysis"
                : activePage === "behavioral-ai"
                ? "Behavioral patterns detected across trading activity"
                : activePage === "ml-predictions"
                ? "Machine-learning based trading outcome signals"
                : "AI-powered behavioral and risk analysis"}
            </div>
          </div>

          <div className="topbar-actions">

            {/* DATA SOURCE SELECTOR */}
            <div className="source-selector">
              <span className="source-label">
                DATA SOURCE
              </span>

              <select
                value={dataSource}
                onChange={(e) => {
                  setDataSource(e.target.value);
                }}
                disabled={refreshing}
                aria-label="Select trading data source"
              >
                <option value="simulator">
                  Demo Simulator · {formatNumber(dashboard?.total_trades || 0)}
                </option>

                <option value="tradingview">
                  Optional CSV Analysis · {formatNumber(dashboard?.total_trades || 0)}
                </option>
              </select>
            </div>

            <button
              className="primary-button"
              onClick={() => {
                setShowImport(true);
                setImportStatus(null);
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "7px",
                padding: "10px 14px",
                fontSize: "12px",
              }}
            >
              <Upload size={15} />
              Import CSV
            </button>

            <div className="live-indicator">
              <span />
              LIVE
            </div>

            <button
              className="refresh-button"
              onClick={loadDashboard}
              disabled={refreshing}
              title="Refresh intelligence"
            >
              <RefreshCw
                size={18}
                className={
                  refreshing ? "spin" : ""
                }
              />
            </button>

          </div>
        </header>

        {/* ==================================================
            PAGE CONTENT
        ================================================== */}

        {activePage === "trading-terminal" ? (
          <TradingTerminal />
        ) : activePage === "trade-analysis" ? (
          dataSource === "simulator" ? (
            <SimulatorTradeAnalysis
              trades={journalTrades}
              dashboard={dashboard}
              onOpenJournal={() => setActivePage("journal")}
            />
          ) : (
            <div className="dashboard-content">
              <TradeAnalysis source={dataSource} />
            </div>
          )
        ) : activePage === "journal" ? (
          <TradeJournalPage
            trades={journalTrades}
            loading={journalLoading}
            search={journalSearch}
            setSearch={setJournalSearch}
            selectedTrade={selectedJournalTrade}
            setSelectedTrade={setSelectedJournalTrade}
            onRefresh={loadJournal}
            onImport={() => {
              setShowImport(true);
              setImportStatus(null);
            }}
          />
        ) : activePage === "risk-intelligence" ? (
          <RiskIntelligencePage dashboard={dashboard} highRiskTrades={highRiskTrades} riskData={riskData} />
        ) : activePage === "trader-profiles" ? (
          <TraderProfilesPage
            dashboard={dashboard}
            highRiskTrades={highRiskTrades}
            dataSource={dataSource}
            traderProfiles={traderProfiles}
          />
        ) : activePage === "behavioral-ai" ? (
          <BehavioralAIPage behaviors={behaviors} highRiskTrades={highRiskTrades} dataSource={dataSource} />
        ) : activePage === "ml-predictions" ? (
          <MLPredictionsPage
            mlMetrics={mlMetrics}
            highRiskTrades={highRiskTrades}
            mlPredictions={mlPredictions}
            dataSource={dataSource}
          />
        ) : (
          <div className="dashboard-content">

            {/* HERO */}
            <section className="hero">

              <div>

                <div className="eyebrow">
                  <Zap size={14} />
                  AI DECISION ENGINE
                </div>

                <h1>
                  Know your trading
                  <span>
                    {" "}before you trade.
                  </span>
                </h1>

                <p>
                  {dataSource === "simulator"
                    ? "Your closed demo trades are journaled automatically. CSV history is analyzed only when you select the optional import workflow."
                    : "TradeMind analyzes imported historical trades for behavioral patterns, risk exposure and explainable AI signals."}
                </p>

              </div>

              <div className="hero-status">

                <div className="hero-status-icon">
                  <Activity size={25} />
                </div>

                <div>
                  <strong>
                    Intelligence Active
                  </strong>

                  <span>
                    {formatNumber(
                      dashboard?.total_trades
                    )}{" "}
                    {dataSource === "tradingview"
                      ? "imported CSV trades"
                      : "closed demo trades"} analyzed
                  </span>
                </div>

              </div>

            </section>

            {/* ==================================================
                KPI CARDS
            ================================================== */}
            <section className="kpi-grid">

              <KpiCard
                icon={<CircleDollarSign />}
                label="Total Trades"
                value={formatNumber(
                  dashboard?.total_trades
                )}
                description={dataSource === "simulator" ? "Closed demo trades journaled" : "Imported CSV trades analyzed"}
                accent="blue"
              />

              <KpiCard
                icon={<Gauge />}
                label="Average Risk"
                value={formatNumber(
                  dashboard?.average_risk_score
                )}
                description="Risk score / 100"
                accent="orange"
              />

              <KpiCard
                icon={<ShieldAlert />}
                label="Discipline Score"
                value={formatNumber(
                  dashboard?.average_discipline_score
                )}
                description="Trader discipline"
                accent="purple"
              />

              <KpiCard
                icon={<TrendingUp />}
                label={dataSource === "simulator" ? "Realized P&L" : "ML Win Probability"}
                value={dataSource === "simulator"
                  ? `$${formatNumber(dashboard?.realized_pnl ?? 0)}`
                  : formatPercent(dashboard?.average_ml_win_probability)}
                description={dataSource === "simulator"
                  ? `${dashboard?.wins ?? 0} wins · ${dashboard?.losses ?? 0} losses`
                  : "Average model signal"}
                accent="green"
              />

            </section>

            {/* ==================================================
                DECISIONS + RISK
            ================================================== */}
            <section className="two-column">

              {/* DECISION INTELLIGENCE */}
              <Panel
                title="Decision Intelligence"
                subtitle="AI-generated trading decisions"
                icon={<BrainCircuit size={18} />}
              >

                <div className="chart-container">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <PieChart>

                      <Pie
                        data={decisionData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={72}
                        outerRadius={105}
                        paddingAngle={3}
                        stroke="none"
                      >

                        {decisionData.map(
                          (entry) => (
                            <Cell
                              key={entry.name}
                              fill={
                                decisionColors[
                                  entry.name
                                ] || "#64748b"
                              }
                            />
                          )
                        )}

                      </Pie>

                      <Tooltip
                        contentStyle={{
                          background: "#111827",
                          border:
                            "1px solid #263247",
                          borderRadius: "10px",
                          color: "#fff",
                        }}
                      />

                    </PieChart>
                  </ResponsiveContainer>

                  <div className="chart-center">

                    <strong>
                      {formatNumber(
                        dashboard?.total_trades
                      )}
                    </strong>

                    <span>
                      TRADES
                    </span>

                  </div>

                </div>

                <div className="legend">

                  {decisionData.map(
                    (item) => (
                      <LegendItem
                        key={item.name}
                        color={
                          decisionColors[
                            item.name
                          ] || "#64748b"
                        }
                        label={item.name}
                        value={item.value}
                      />
                    )
                  )}

                </div>

              </Panel>

              {/* RISK DISTRIBUTION */}
              <Panel
                title="Risk Distribution"
                subtitle="Portfolio behavioral risk"
                icon={<ShieldAlert size={18} />}
              >

                <div className="chart-container">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <PieChart>

                      <Pie
                        data={riskData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={72}
                        outerRadius={105}
                        paddingAngle={3}
                        stroke="none"
                      >

                        {riskData.map(
                          (entry) => (
                            <Cell
                              key={entry.name}
                              fill={
                                riskColors[
                                  entry.name
                                ] || "#64748b"
                              }
                            />
                          )
                        )}

                      </Pie>

                      <Tooltip
                        contentStyle={{
                          background: "#111827",
                          border:
                            "1px solid #263247",
                          borderRadius: "10px",
                          color: "#fff",
                        }}
                      />

                    </PieChart>
                  </ResponsiveContainer>

                  <div className="chart-center">

                    <strong>
                      {formatNumber(
                        dashboard
                          ?.risk_distribution
                          ?.CRITICAL || 0
                      )}
                    </strong>

                    <span>
                      CRITICAL
                    </span>

                  </div>

                </div>

                <div className="legend">

                  {riskData.map(
                    (item) => (
                      <LegendItem
                        key={item.name}
                        color={
                          riskColors[
                            item.name
                          ] || "#64748b"
                        }
                        label={item.name}
                        value={item.value}
                      />
                    )
                  )}

                </div>

              </Panel>

            </section>

            {/* ==================================================
                BEHAVIOR + ML
            ================================================== */}
            <section className="two-column">

              {/* BEHAVIORAL INTELLIGENCE */}
              <Panel
                title="Behavioral Intelligence"
                subtitle="Detected high-risk trading patterns"
                icon={<Activity size={18} />}
              >

                {behaviorData.length > 0 ? (

                  <div className="behavior-chart">

                    <ResponsiveContainer
                      width="100%"
                      height="100%"
                    >
                      <BarChart
                        data={behaviorData}
                        layout="vertical"
                        margin={{
                          top: 5,
                          right: 20,
                          left: 10,
                          bottom: 5,
                        }}
                      >

                        <CartesianGrid
                          stroke="#1e293b"
                          horizontal={false}
                        />

                        <XAxis
                          type="number"
                          stroke="#64748b"
                          fontSize={11}
                        />

                        <YAxis
                          type="category"
                          dataKey="name"
                          stroke="#94a3b8"
                          fontSize={11}
                          width={100}
                        />

                        <Tooltip
                          contentStyle={{
                            background: "#111827",
                            border:
                              "1px solid #263247",
                            borderRadius: "10px",
                          }}
                        />

                        <Bar
                          dataKey="value"
                          fill="#8b5cf6"
                          radius={[
                            0,
                            5,
                            5,
                            0,
                          ]}
                        />

                      </BarChart>
                    </ResponsiveContainer>

                  </div>

                ) : (

                  <EmptyState
                    text="Behavior data unavailable"
                  />

                )}

              </Panel>

              {/* ML MODEL PERFORMANCE */}
              <Panel
                title="ML Model Performance"
                subtitle={
                  mlMetrics?.validation ||
                  "Trusted model validation"
                }
                icon={<Target size={18} />}
              >

                <div className="model-name">

                  <div className="model-icon">
                    <BrainCircuit size={21} />
                  </div>

                  <div>

                    <strong>
                      {mlMetrics?.model ||
                        "Trusted ML Model"}
                    </strong>

                    <span>
                      Temporal validation
                    </span>

                  </div>

                </div>

                <div className="metric-grid">

                  <Metric
                    label="Accuracy"
                    value={formatPercent(
                      ml.accuracy
                    )}
                  />

                  <Metric
                    label="Precision"
                    value={formatPercent(
                      ml.precision
                    )}
                  />

                  <Metric
                    label="Recall"
                    value={formatPercent(
                      ml.recall
                    )}
                  />

                  <Metric
                    label="F1 Score"
                    value={formatPercent(
                      ml.f1
                    )}
                  />

                  <Metric
                    label="ROC-AUC"
                    value={formatNumber(
                      ml.roc_auc
                    )}
                  />

                  <Metric
                    label="PR-AUC"
                    value={formatNumber(
                      ml.pr_auc
                    )}
                  />

                </div>

              </Panel>

            </section>

            {/* ==================================================
                HIGH RISK TRADES
            ================================================== */}
            <Panel
              title="High-Risk Trade Monitor"
              subtitle="Trades requiring immediate attention"
              icon={<AlertTriangle size={18} />}
              action={
                <button className="view-all">
                  View all
                  <ChevronRight size={15} />
                </button>
              }
            >

              <div className="risk-table-wrapper">

                <table className="risk-table">

                  <thead>

                    <tr>
                      <th>TRADE</th>
                      <th>SYMBOL</th>
                      <th>RISK</th>
                      <th>LEVEL</th>
                      <th>DISCIPLINE</th>
                      <th>BEHAVIORS</th>
                      <th>DECISION</th>
                    </tr>

                  </thead>

                  <tbody>

                    {highRiskTrades.length > 0 ? (

                      highRiskTrades
                        .slice(0, 8)
                        .map(
                          (trade, index) => (

                            <tr
                              key={
                                trade.trade_id ||
                                trade.id ||
                                index
                              }
                            >

                              <td>
                                <strong className="trade-id">
                                  {trade.trade_id ||
                                    trade.id ||
                                    "—"}
                                </strong>
                              </td>

                              <td>
                                <span className="symbol">
                                  {trade.symbol ||
                                    "—"}
                                </span>
                              </td>

                              <td>

                                <div className="risk-score">

                                  {formatNumber(
                                    trade.risk_score
                                  )}

                                  <span>
                                    /100
                                  </span>

                                </div>

                              </td>

                              <td>

                                <RiskBadge
                                  level={
                                    trade.risk_level ||
                                    "UNKNOWN"
                                  }
                                />

                              </td>

                              <td>

                                {formatNumber(
                                  trade.discipline_score
                                )}

                              </td>

                              <td>

                                <div className="behavior-tags">

                                  {String(
                                    trade.behaviors ||
                                      ""
                                  )
                                    .split(", ")
                                    .filter(Boolean)
                                    .slice(0, 3)
                                    .map(
                                      (
                                        behavior
                                      ) => (
                                        <span
                                          className="behavior-tag"
                                          key={
                                            behavior
                                          }
                                        >
                                          {behavior}
                                        </span>
                                      )
                                    )}

                                </div>

                              </td>

                              <td>

                                <DecisionBadge
                                  decision={
                                    trade.decision ||
                                    "—"
                                  }
                                />

                              </td>

                            </tr>

                          )
                        )

                    ) : (

                      <tr>

                        <td colSpan="7">

                          <EmptyState
                            text="No high-risk trade data available"
                          />

                        </td>

                      </tr>

                    )}

                  </tbody>

                </table>

              </div>

            </Panel>

            {/* ==================================================
                FOOTER
            ================================================== */}
            <footer className="footer">

              <span>
                TradeMind AI • Behavioral Trading Intelligence
              </span>

              <span>
                Powered by FastAPI + Machine Learning
              </span>

            </footer>

          </div>
        )}

        {showImport && (
          <TradingViewImportModal
            file={importFile}
            setFile={setImportFile}
            importing={importing}
            status={importStatus}
            onClose={() => {
              if (!importing) {
                setShowImport(false);
                setImportFile(null);
                setImportStatus(null);
              }
            }}
            onImport={async () => {
              const success = await handleTradingViewImport();
              if (success) setShowImport(false);
            }}
          />
        )}

      </main>
    </div>
  );
}

/* ============================================================
   RISK INTELLIGENCE PAGE
============================================================ */

function SimulatorTradeAnalysis({ trades, dashboard, onOpenJournal }) {
  const rows = (trades || []).filter((trade) => trade.closed_at || trade.exit_time);
  const pnlOf = (trade) => {
    const value = Number(trade.realized_pnl ?? trade.net_pnl ?? trade.pnl);
    return Number.isFinite(value) ? value : 0;
  };
  const wins = rows.filter((trade) => pnlOf(trade) > 0).length;
  const losses = rows.filter((trade) => pnlOf(trade) < 0).length;
  const net = rows.reduce((sum, trade) => sum + pnlOf(trade), 0);
  const avgWin = wins ? rows.filter((trade) => pnlOf(trade) > 0).reduce((sum, trade) => sum + pnlOf(trade), 0) / wins : 0;
  const avgLoss = losses ? rows.filter((trade) => pnlOf(trade) < 0).reduce((sum, trade) => sum + pnlOf(trade), 0) / losses : 0;

  return (
    <div className="dashboard-content">
      <section className="hero">
        <div>
          <div className="eyebrow"><Activity size={14} /> DEMO TRADE REVIEW</div>
          <h1>Trade Analysis</h1>
          <p>Analysis from your actual closed simulator trades. Statistics update when trades are closed and journaled.</p>
        </div>
        <div className="hero-status">
          <div className="hero-status-icon"><Activity size={25} /></div>
          <div><strong>Simulator Analytics</strong><span>{formatNumber(rows.length)} closed trades</span></div>
        </div>
      </section>
      <section className="kpi-grid">
        <KpiCard icon={<BookOpen />} label="Closed Trades" value={formatNumber(rows.length)} description="Recorded simulator exits" accent="blue" />
        <KpiCard icon={<TrendingUp />} label="Win Rate" value={rows.length ? `${((wins / rows.length) * 100).toFixed(1)}%` : "—"} description={`${wins} wins · ${losses} losses`} accent="green" />
        <KpiCard icon={<CircleDollarSign />} label="Net Realized P&L" value={`${net >= 0 ? "+" : ""}$${formatNumber(net)}`} description="From recorded exits" accent={net >= 0 ? "green" : "orange"} />
        <KpiCard icon={<Gauge />} label="Average Risk" value={formatNumber(dashboard?.average_risk_score)} description="Recorded rule-based score / 100" accent="purple" />
      </section>
      <section className="two-column">
        <Panel title="Outcome Summary" subtitle="Calculated from realized simulator P&L" icon={<TrendingUp size={18} />}>
          <div className="metric-grid">
            <Metric label="Average Winning Trade" value={wins ? `$${formatNumber(avgWin)}` : "—"} />
            <Metric label="Average Losing Trade" value={losses ? `$${formatNumber(avgLoss)}` : "—"} />
            <Metric label="Average R Multiple" value={dashboard?.average_r_multiple == null ? "—" : `${Number(dashboard.average_r_multiple).toFixed(2)}R`} />
            <Metric label="Total Realized P&L" value={`${net >= 0 ? "+" : ""}$${formatNumber(net)}`} />
          </div>
        </Panel>
        <Panel title="Review Notes" subtitle="What this analysis can and cannot say" icon={<BrainCircuit size={18} />}>
          <p style={{ color: "#cbd5e1", lineHeight: 1.7, marginTop: 0 }}>
            Results are calculated from recorded demo executions and journal fields. Behavioral notes are rule-based coaching; no ML win probability is claimed for simulator trades unless a trained model is explicitly connected.
          </p>
          <button className="primary-button" onClick={onOpenJournal}>Open Trade Journal</button>
        </Panel>
      </section>
      <Panel title="Recent Closed Trades" subtitle="Latest simulator exits" icon={<BookOpen size={18} />}>
        {rows.length ? (
          <div className="risk-table-wrapper"><table className="risk-table">
            <thead><tr><th>TRADE</th><th>SYMBOL</th><th>SIDE</th><th>ENTRY</th><th>EXIT</th><th>REALIZED P&L</th><th>EXIT REASON</th></tr></thead>
            <tbody>{rows.slice(0, 20).map((trade, index) => {
              const value = pnlOf(trade);
              return <tr key={trade.trade_id || trade.id || index}>
                <td><strong className="trade-id">{trade.trade_id || trade.id || "—"}</strong></td>
                <td>{trade.symbol || "—"}</td><td>{trade.side || trade.direction || "—"}</td>
                <td>{formatNumber(trade.entry_price)}</td><td>{formatNumber(trade.exit_price)}</td>
                <td style={{ color: value >= 0 ? "#4ade80" : "#fb7185" }}>{value >= 0 ? "+" : ""}${formatNumber(value)}</td>
                <td>{String(trade.close_reason || "MANUAL").replaceAll("_", " ")}</td>
              </tr>;
            })}</tbody>
          </table></div>
        ) : <EmptyState text="No closed demo trades yet. Close a demo position to populate Trade Analysis from real execution records." />}
      </Panel>
    </div>
  );
}

/* ============================================================
   TRADE JOURNAL
============================================================ */
function TradeJournalPage({
  trades,
  loading,
  search,
  setSearch,
  selectedTrade,
  setSelectedTrade,
  onRefresh,
  onImport,
}) {
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return trades;
    return trades.filter((t) =>
      [
        t.trade_id,
        t.id,
        t.symbol,
        t.account,
        t.direction,
        t.side,
        t.decision,
        t.risk_level,
        t.behaviors,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [trades, search]);

  const total = trades.length;
  const highRisk = trades.filter((t) =>
    ["HIGH", "CRITICAL"].includes(String(t.risk_level || "").toUpperCase())
  ).length;
  const avgRisk =
    total > 0
      ? trades.reduce((sum, t) => sum + (Number(t.risk_score) || 0), 0) / total
      : 0;

  return (
    <div className="dashboard-content">
      <section className="hero">
        <div>
          <div className="eyebrow">
            <BookOpen size={14} /> AI TRADING JOURNAL
          </div>
          <h1>Trade Journal</h1>
          <p>
            Review automatically journaled simulator exits alongside imported TradingView trades and their TradeMind analysis.
          </p>
        </div>

        <div className="hero-status">
          <div className="hero-status-icon">
            <BookOpen size={25} />
          </div>
          <div>
            <strong>Journal Engine Active</strong>
            <span>{formatNumber(total)} trades loaded</span>
          </div>
        </div>
      </section>

      <section className="kpi-grid">
        <KpiCard
          icon={<BookOpen />}
          label="Journal Trades"
          value={formatNumber(total)}
          description="Auto exits + imported records"
          accent="blue"
        />
        <KpiCard
          icon={<Gauge />}
          label="Average Risk"
          value={formatNumber(avgRisk)}
          description="Risk score / 100"
          accent="orange"
        />
        <KpiCard
          icon={<AlertTriangle />}
          label="High / Critical"
          value={formatNumber(highRisk)}
          description="Trades needing review"
          accent="red"
        />
        <KpiCard
          icon={<BrainCircuit />}
          label="AI Enriched"
          value={total ? "YES" : "—"}
          description="Behavior + risk + ML pipeline"
          accent="purple"
        />
      </section>
        <SimulatorJournalInsights />


      <Panel
        title="Automatic + Imported Trade Journal"
        subtitle="Closed simulator trades are journaled automatically; TradingView imports retain their AI analysis."
        icon={<BookOpen size={18} />}
        action={
          <div style={{ display: "flex", gap: "8px" }}>
            <button className="view-all" onClick={onRefresh} disabled={loading}>
              <RefreshCw size={15} className={loading ? "spin" : ""} />
              Refresh
            </button>
            <button className="view-all" onClick={onImport}>
              <Upload size={15} />
              Import CSV
            </button>
          </div>
        }
      >
        <div
          style={{
            display: "flex",
            gap: "10px",
            marginBottom: "16px",
            alignItems: "center",
          }}
        >
          <div style={{ position: "relative", flex: 1 }}>
            <Search
              size={16}
              style={{
                position: "absolute",
                left: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "#64748b",
              }}
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search trade, symbol, account, decision, behavior..."
              style={{
                width: "100%",
                boxSizing: "border-box",
                background: "#0b1220",
                border: "1px solid #263247",
                borderRadius: "10px",
                padding: "11px 12px 11px 38px",
                color: "#e2e8f0",
                outline: "none",
              }}
            />
          </div>
          <span className="panel-meta">
            {formatNumber(filtered.length)} shown
          </span>
        </div>

        {loading ? (
          <EmptyState text="Loading journal trades..." />
        ) : filtered.length === 0 ? (
          <EmptyState text="No closed simulator trades or imported journal records yet. Close a demo trade to create an automatic journal entry." />
        ) : (
          <div className="risk-table-wrapper">
            <table className="risk-table">
              <thead>
                <tr>
                  <th>TRADE</th>
                  <th>SYMBOL</th>
                  <th>SIDE</th>
                  <th>RISK</th>
                  <th>ML PROB.</th>
                  <th>BEHAVIOR</th>
                  <th>DECISION</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 100).map((trade, index) => (
                  <tr key={trade.trade_id || trade.id || index}>
                    <td>
                      <strong className="trade-id">
                        {trade.trade_id || trade.id || `TRADE-${index + 1}`}
                      </strong>
                    </td>
                    <td>{trade.symbol || "—"}</td>
                    <td>{trade.direction || trade.side || "—"}</td>
                    <td>
                      <RiskBadge level={trade.risk_level || "UNKNOWN"} />
                    </td>
                    <td>
                      {formatPercent(
                        trade.ml_win_probability ??
                          trade.win_probability ??
                          trade.predicted_probability
                      )}
                    </td>
                    <td>
                      <div className="behavior-tags">
                        {String(trade.behaviors || "")
                          .split(",")
                          .map((x) => x.trim())
                          .filter(Boolean)
                          .slice(0, 2)
                          .map((b) => (
                            <span className="behavior-tag" key={b}>
                              {b}
                            </span>
                          ))}
                      </div>
                    </td>
                    <td>
                      <DecisionBadge decision={trade.decision || "—"} />
                    </td>
                    <td>
                      <button
                        className="view-all"
                        onClick={() => setSelectedTrade(trade)}
                      >
                        View
                        <ChevronRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {filtered.length > 100 && (
          <div style={{ marginTop: "12px", color: "#64748b", fontSize: "12px" }}>
            Showing first 100 matching trades. Use search to narrow the journal.
          </div>
        )}
      </Panel>

      {selectedTrade && (
        <TradeJournalDetail
          trade={selectedTrade}
          onClose={() => setSelectedTrade(null)}
        />
      )}
    </div>
  );
}



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

function TradeJournalDetail({ trade, onClose }) {
  const [detail, setDetail] = useState(trade || {});
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    const tradeId = trade?.trade_id || trade?.id;
    if (!tradeId) return;
    if (trade?.source === "simulator_auto" || String(tradeId).startsWith("SIM-TRD-")) {
      setDetail(trade || {});
      setLoadingDetail(false);
      return;
    }

    let cancelled = false;

    const loadDetail = async () => {
      setLoadingDetail(true);
      try {
        const response = await api.get(
          `/api/tradingview/trades/${encodeURIComponent(tradeId)}`
        );
        if (!cancelled) {
          const payload = response?.data || {};
          const apiTrade = payload.trade || {};
          setDetail({
            ...trade,
            ...apiTrade,
            behaviors: apiTrade.behaviors || trade.behaviors,
            behaviorRecords: payload.behaviors || [],
            riskRecord: payload.risk?.[0] || null,
            featureRecord: payload.features?.[0] || null,
          });
        }
      } catch (error) {
        console.error("Could not load TradingView trade detail:", error);
        if (!cancelled) setDetail(trade || {});
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    };

    loadDetail();

    return () => {
      cancelled = true;
    };
  }, [trade]);

  const valueOrDash = (value) =>
    value === undefined || value === null || value === "" ? "—" : value;

  const formatPrice = (value) => {
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 5,
    }) : valueOrDash(value);
  };

  const formatMoney = (value) => {
    const n = Number(value);
    return Number.isFinite(n)
      ? n.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : valueOrDash(value);
  };

  const behaviors = detail.behaviorRecords || [];
  const riskRecord = detail.riskRecord || {};

  const fields = [
    ["Trade ID", detail.trade_id || detail.id],
    ["Account", detail.account],
    ["Symbol", detail.symbol],
    ["Direction", detail.direction || detail.side],
    ["Quantity", detail.quantity ?? detail.qty],
    ["Entry Price", formatPrice(detail.entry_price ?? detail.fill_price)],
    ["Exit Price", formatPrice(detail.exit_price)],
    ["P&L", formatMoney(detail.net_pnl ?? detail.pnl ?? detail.profit ?? detail.realized_pnl)],
    ["Setup", detail.setup_type],
    ["Strategy", detail.strategy_name],
    ["Entry Thesis", detail.entry_reason],
    ["Entry Emotion", detail.emotion],
    ["Entry Confidence", detail.confidence != null ? `${detail.confidence}/10` : "—"],
    ["Exit Reason", detail.close_reason],
    ["R Multiple", detail.r_multiple != null ? `${detail.r_multiple}R` : "—"],
    ["Exit Reason", detail.close_reason],
    ["R Multiple", detail.r_multiple != null ? `${detail.r_multiple}R` : "—"],
    ["Holding Time", detail.holding_minutes != null ? `${detail.holding_minutes} min` : "—"],
    ["Entry Time", detail.entry_time],
    ["Exit Time", detail.exit_time],
    ["Risk Score", detail.risk_score != null ? `${formatNumber(detail.risk_score)} / 100` : "—"],
    ["Risk Level", detail.risk_level],
    ["Discipline", detail.discipline_score != null ? formatNumber(detail.discipline_score) : "—"],
    ["ML Win Probability", formatPercent(
      detail.ml_win_probability ??
        detail.win_probability ??
        detail.predicted_probability
    )],
    ["ML Signal", detail.ml_signal],
    ["Decision", detail.decision],
  ];

  return (
    <div
      style={{
        marginTop: "16px",
        border: "1px solid #263247",
        borderRadius: "14px",
        background: "#0b1220",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 18px",
          borderBottom: "1px solid #1e293b",
        }}
      >
        <div>
          <div className="eyebrow">
            <BrainCircuit size={14} /> TRADEMIND ANALYSIS
          </div>
          <h2 style={{ margin: "6px 0 0" }}>
            {trade.trade_id || trade.id || "Selected Trade"}
          </h2>
        </div>
        <button className="refresh-button" onClick={onClose}>
          <X size={17} />
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "10px",
          padding: "16px",
        }}
      >
        {fields.map(([label, value]) => (
          <div
            key={label}
            style={{
              padding: "12px",
              border: "1px solid #1e293b",
              borderRadius: "10px",
              background: "#0f172a",
            }}
          >
            <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase" }}>
              {label}
            </div>
            <div style={{ color: "#e2e8f0", fontWeight: 700, marginTop: "5px" }}>
              {value === undefined || value === null || value === "" ? "—" : value}
            </div>
          </div>
        ))}
      </div>

      {detail.source === "simulator_auto" && (
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

      {detail.source === "simulator_auto" && detail.market_snapshot && (
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

      <div style={{ padding: "0 16px 16px" }}>
        <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>
          Detected Behaviors
        </div>
        {loadingDetail ? (
          <div style={{ color: "#94a3b8", fontSize: "13px" }}>Loading behavioral analysis...</div>
        ) : behaviors.length > 0 ? (
          <div style={{ display: "grid", gap: "8px" }}>
            {behaviors.map((item, index) => (
              <div
                key={`${item.behavior || "behavior"}-${index}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(140px, 1fr) auto",
                  gap: "10px",
                  padding: "10px 12px",
                  border: "1px solid #1e293b",
                  borderRadius: "10px",
                  background: "#0f172a",
                }}
              >
                <div>
                  <strong style={{ color: "#e2e8f0", fontSize: "13px" }}>
                    {item.behavior || "Behavior"}
                  </strong>
                  <div style={{ color: "#64748b", fontSize: "11px", marginTop: "4px" }}>
                    {item.evidence || "No evidence provided"}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <RiskBadge level={item.severity || "UNKNOWN"} />
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginTop: "5px" }}>
                    Score {formatNumber(item.score)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="behavior-tags">
            {String(detail.behaviors || "No behavior flags")
              .split(",")
              .map((x) => x.trim())
              .filter(Boolean)
              .map((b) => (
                <span className="behavior-tag" key={b}>
                  {b}
                </span>
              ))}
          </div>
        )}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "12px",
          padding: "0 16px 16px",
        }}
      >
        <div style={{ padding: "14px", border: "1px solid #1e293b", borderRadius: "10px", background: "#0f172a" }}>
          <div style={{ color: "#8b5cf6", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", marginBottom: "8px" }}>
            Risk Intelligence
          </div>
          <div style={{ color: "#e2e8f0", fontWeight: 700 }}>
            {detail.risk_level || "UNKNOWN"} · {formatNumber(detail.risk_score)} / 100
          </div>
          <div style={{ color: "#94a3b8", fontSize: "12px", marginTop: "6px" }}>
            {riskRecord.recommendation || detail.primary_risk || "No additional risk recommendation."}
          </div>
          {riskRecord.reasons && (
            <div style={{ color: "#64748b", fontSize: "11px", marginTop: "8px", lineHeight: 1.5 }}>
              {riskRecord.reasons}
            </div>
          )}
        </div>

        <div style={{ padding: "14px", border: "1px solid #1e293b", borderRadius: "10px", background: "#0f172a" }}>
          <div style={{ color: "#8b5cf6", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", marginBottom: "8px" }}>
            ML Intelligence
          </div>
          <div style={{ color: "#e2e8f0", fontWeight: 700 }}>
            Win {formatPercent(detail.ml_win_probability)} · Loss {formatPercent(detail.ml_loss_probability)}
          </div>
          <div style={{ color: "#94a3b8", fontSize: "12px", marginTop: "6px" }}>
            Signal: {detail.ml_signal || "—"}
          </div>
        </div>
      </div>

      <div style={{ padding: "0 16px 16px" }}>
        <div style={{ padding: "14px", border: "1px solid #1e293b", borderRadius: "10px", background: "#0f172a" }}>
          <div style={{ color: "#8b5cf6", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", marginBottom: "8px" }}>
            AI Decision
          </div>
          <div style={{ color: "#e2e8f0", fontWeight: 800, fontSize: "16px" }}>
            {detail.decision || "—"}
          </div>
          <div style={{ color: "#94a3b8", fontSize: "12px", lineHeight: 1.6, marginTop: "8px" }}>
            {detail.recommendation || "No recommendation available."}
          </div>
          {detail.reasons && (
            <div style={{ color: "#64748b", fontSize: "11px", lineHeight: 1.6, marginTop: "8px" }}>
              {detail.reasons}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TradingViewImportModal({
  file,
  setFile,
  importing,
  status,
  onClose,
  onImport,
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(2, 6, 23, 0.78)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        style={{
          width: "min(560px, 100%)",
          background: "#0f172a",
          border: "1px solid #263247",
          borderRadius: "16px",
          boxShadow: "0 24px 80px rgba(0,0,0,.45)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "18px 20px",
            borderBottom: "1px solid #1e293b",
          }}
        >
          <div>
            <div className="eyebrow">
              <Upload size={14} /> TRADINGVIEW PAPER
            </div>
            <h2 style={{ margin: "6px 0 0" }}>Import Trading Journal</h2>
          </div>
          <button className="refresh-button" onClick={onClose} disabled={importing}>
            <X size={17} />
          </button>
        </div>

        <div style={{ padding: "20px" }}>
          <div
            style={{
              border: "1px dashed #475569",
              borderRadius: "12px",
              padding: "28px 18px",
              textAlign: "center",
              background: "#0b1220",
            }}
          >
            <Upload size={28} style={{ marginBottom: "10px" }} />
            <div style={{ color: "#e2e8f0", fontWeight: 700 }}>
              Select TradingView CSV
            </div>
            <div style={{ color: "#64748b", fontSize: "12px", margin: "6px 0 16px" }}>
              Export your filled Paper Trading history as CSV.
            </div>

            <input
              id="tradingview-csv"
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              style={{ display: "none" }}
            />
            <label
              htmlFor="tradingview-csv"
              className="primary-button"
              style={{ display: "inline-flex", cursor: "pointer" }}
            >
              Choose CSV
            </label>

            {file && (
              <div style={{ marginTop: "14px", color: "#cbd5e1", fontSize: "13px" }}>
                Selected: <strong>{file.name}</strong>
              </div>
            )}
          </div>

          {status && (
            <div
              style={{
                marginTop: "14px",
                padding: "12px 14px",
                borderRadius: "10px",
                border: `1px solid ${status.type === "success" ? "#14532d" : "#7f1d1d"}`,
                background: status.type === "success" ? "#052e16" : "#450a0a",
                color: "#e2e8f0",
                display: "flex",
                gap: "9px",
                alignItems: "flex-start",
                fontSize: "13px",
              }}
            >
              {status.type === "success" ? (
                <CheckCircle2 size={17} />
              ) : (
                <AlertTriangle size={17} />
              )}
              <span>{status.message}</span>
            </div>
          )}

          <div
            style={{
              marginTop: "16px",
              padding: "12px 14px",
              borderRadius: "10px",
              background: "#111827",
              color: "#94a3b8",
              fontSize: "12px",
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: "#cbd5e1" }}>Pipeline:</strong>{" "}
            TradingView CSV → normalization → TradeMind features → Behavioral
            AI → Risk Engine → ML → Decision Engine → Journal.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "9px",
            padding: "14px 20px",
            borderTop: "1px solid #1e293b",
          }}
        >
          <button className="view-all" onClick={onClose} disabled={importing}>
            Cancel
          </button>
          <button
            className="primary-button"
            onClick={onImport}
            disabled={!file || importing}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              opacity: !file || importing ? 0.55 : 1,
            }}
          >
            <Upload size={15} />
            {importing ? "Analyzing..." : "Import & Analyze"}
          </button>
        </div>
      </div>
    </div>
  );
}

function RiskIntelligencePage({ dashboard, highRiskTrades, riskData }) {
  const total = Number(dashboard?.total_trades) || 0;
  const average = Number(dashboard?.average_risk_score) || 0;
  const critical = Number(dashboard?.risk_distribution?.CRITICAL) || 0;
  const high = Number(dashboard?.risk_distribution?.HIGH) || 0;
  const medium = Number(dashboard?.risk_distribution?.MEDIUM) || 0;
  const low = Number(dashboard?.risk_distribution?.LOW) || 0;
  return (
    <div className="dashboard-content">
      <section className="hero"><div><div className="eyebrow"><ShieldAlert size={14}/> RISK INTELLIGENCE</div><h1>Risk Intelligence</h1><p>Understand portfolio risk exposure, behavioral risk and high-risk trades.</p></div><div className="hero-status"><div className="hero-status-icon"><ShieldAlert size={25}/></div><div><strong>Risk Engine Active</strong><span>{formatNumber(total)} trades classified</span></div></div></section>
      <section className="kpi-grid"><KpiCard icon={<Gauge/>} label="Average Risk" value={formatNumber(average)} description="Portfolio risk score / 100" accent="orange"/><KpiCard icon={<AlertTriangle/>} label="Critical Trades" value={formatNumber(critical)} description="Immediate attention required" accent="red"/><KpiCard icon={<ShieldAlert/>} label="High Risk" value={formatNumber(high)} description="High behavioral risk" accent="orange"/><KpiCard icon={<Activity/>} label="Analyzed Trades" value={formatNumber(total)} description="Risk-classified trades" accent="purple"/></section>
      <section className="two-column"><Panel title="Risk Distribution" subtitle="Current risk composition" icon={<ShieldAlert size={18}/>}><div className="chart-container"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={riskData} dataKey="value" nameKey="name" innerRadius={72} outerRadius={105} paddingAngle={3} stroke="none">{riskData.map(e=><Cell key={e.name} fill={riskColors[e.name]||"#64748b"}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer><div className="chart-center"><strong>{formatNumber(critical)}</strong><span>CRITICAL</span></div></div><div className="legend"><LegendItem color={riskColors.LOW} label="LOW" value={low}/><LegendItem color={riskColors.MEDIUM} label="MEDIUM" value={medium}/><LegendItem color={riskColors.HIGH} label="HIGH" value={high}/><LegendItem color={riskColors.CRITICAL} label="CRITICAL" value={critical}/></div></Panel><Panel title="Risk Interpretation" subtitle="TradeMind risk engine" icon={<BrainCircuit size={18}/>}><div className="model-name"><div className="model-icon"><ShieldAlert size={21}/></div><div><strong>Behavioral Risk Analysis</strong><span>Risk scoring + behavioral signals</span></div></div><div style={{marginTop:"18px",color:"#94a3b8",lineHeight:"1.7"}}>TradeMind classifies trading activity into LOW, MEDIUM, HIGH and CRITICAL behavioral-risk categories.<br/><br/>Higher-risk trades receive additional review so recurring patterns can be investigated.</div></Panel></section>
      <Panel title="Highest Risk Trades" subtitle="Trades requiring the most attention" icon={<AlertTriangle size={18}/>} action={<div className="panel-meta">{highRiskTrades.length} flagged</div>}><div className="risk-table-wrapper"><table className="risk-table"><thead><tr><th>TRADE</th><th>SYMBOL</th><th>DIRECTION</th><th>RISK SCORE</th><th>RISK LEVEL</th><th>DECISION</th></tr></thead><tbody>{highRiskTrades.slice(0,10).map((trade,i)=><tr key={trade.trade_id||i}><td><strong className="trade-id">{trade.trade_id||"—"}</strong></td><td>{trade.symbol||"—"}</td><td>{trade.direction||"—"}</td><td><div className="risk-score">{formatNumber(trade.risk_score)}<span>/100</span></div></td><td><RiskBadge level={trade.risk_level||"UNKNOWN"}/></td><td><DecisionBadge decision={trade.decision||"—"}/></td></tr>)}</tbody></table></div></Panel>
    </div>
  );
}

function TraderProfilesPage({ dashboard, highRiskTrades, dataSource, traderProfiles }) {
  const accounts = [
    ...new Set(
      [
        ...traderProfiles.map((profile) => profile.account),
        ...highRiskTrades.map((trade) => trade.account),
      ].filter(Boolean)
    ),
  ];

  return (
    <div className="dashboard-content">
      <section className="hero">
        <div>
          <div className="eyebrow">
            <UserRound size={14} /> TRADER INTELLIGENCE
          </div>
          <h1>Trader Profiles</h1>
          <p>
            Account-level behavioral intelligence for the selected data source.
          </p>
        </div>
        <div className="hero-status">
          <div className="hero-status-icon">
            <UserRound size={25} />
          </div>
          <div>
            <strong>Profile Engine Active</strong>
            <span>
              {formatNumber(accounts.length)} account
              {accounts.length === 1 ? "" : "s"} analyzed
            </span>
          </div>
        </div>
      </section>

      <section className="kpi-grid">
        <KpiCard
          icon={<UserRound />}
          label="Visible Accounts"
          value={formatNumber(accounts.length)}
          description="Accounts in current source"
          accent="purple"
        />
        <KpiCard
          icon={<CircleDollarSign />}
          label="Total Trades"
          value={formatNumber(dashboard?.total_trades)}
          description="Current data source"
          accent="blue"
        />
        <KpiCard
          icon={<Gauge />}
          label="Average Risk"
          value={formatNumber(dashboard?.average_risk_score)}
          description="Risk score / 100"
          accent="orange"
        />
        <KpiCard
          icon={<ShieldAlert />}
          label="Critical Trades"
          value={formatNumber(dashboard?.risk_distribution?.CRITICAL)}
          description="Critical risk events"
          accent="red"
        />
      </section>

      <Panel
        title="Trader Profile Intelligence"
        subtitle={
          dataSource === "tradingview"
            ? "TradingView Paper account profile"
            : dataSource === "simulator" ? "Demo simulator journal" : "Historical account profiles"
        }
        icon={<UserRound size={18} />}
      >
        {traderProfiles.length > 0 ? (
          <div className="risk-table-wrapper">
            <table className="risk-table">
              <thead>
                <tr>
                  <th>ACCOUNT</th>
                  <th>TRADES</th>
                  <th>RISK</th>
                  <th>DISCIPLINE</th>
                  <th>BEHAVIOR SCORE</th>
                  <th>WIN RATE</th>
                </tr>
              </thead>
              <tbody>
                {traderProfiles.slice(0, 20).map((profile, index) => (
                  <tr key={profile.account || profile.trader_id || index}>
                    <td>
                      <strong className="trade-id">
                        {profile.account || profile.trader_id || "—"}
                      </strong>
                    </td>
                    <td>
                      {formatNumber(
                        profile.total_trades ??
                          profile.trade_count ??
                          profile.trades
                      )}
                    </td>
                    <td>
                      {formatNumber(
                        profile.average_risk_score ??
                          profile.avg_risk_score ??
                          profile.risk_score
                      )}
                    </td>
                    <td>
                      {formatNumber(
                        profile.discipline_score ??
                          profile.average_discipline_score
                      )}
                    </td>
                    <td>
                      {formatNumber(
                        profile.behavior_score ??
                          profile.average_behavior_score
                      )}
                    </td>
                    <td>
                      {formatPercent(
                        profile.win_rate ??
                          profile.win_probability ??
                          profile.average_ml_win_probability
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState text="No trader profile data available" />
        )}
      </Panel>

      <Panel
        title="Accounts Requiring Attention"
        subtitle={
          dataSource === "tradingview"
            ? "TradingView Paper risk view"
            : dataSource === "simulator" ? "Demo simulator risk view" : "Historical risk view"
        }
        icon={<AlertTriangle size={18} />}
      >
        <div className="risk-table-wrapper">
          <table className="risk-table">
            <thead>
              <tr>
                <th>ACCOUNT</th>
                <th>TRADE</th>
                <th>SYMBOL</th>
                <th>RISK</th>
                <th>DECISION</th>
              </tr>
            </thead>
            <tbody>
              {highRiskTrades.length > 0 ? (
                highRiskTrades.slice(0, 12).map((trade, index) => (
                  <tr key={trade.trade_id || index}>
                    <td>{trade.account || "—"}</td>
                    <td>{trade.trade_id || "—"}</td>
                    <td>{trade.symbol || "—"}</td>
                    <td>
                      <RiskBadge level={trade.risk_level || "UNKNOWN"} />
                    </td>
                    <td>
                      <DecisionBadge decision={trade.decision || "—"} />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5">
                    <EmptyState text="No high-risk accounts found" />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function BehavioralAIPage({ behaviors, highRiskTrades, dataSource }) {
  const total=behaviors.reduce((s,x)=>s+(Number(x.value)||0),0); const list=[...behaviors].sort((a,b)=>b.value-a.value);
  return <div className="dashboard-content"><section className="hero"><div><div className="eyebrow"><BrainCircuit size={14}/> BEHAVIORAL INTELLIGENCE</div><h1>Behavioral AI</h1><p>Detect recurring trading patterns and behavioral risk signals.</p></div></section><section className="kpi-grid"><KpiCard icon={<BrainCircuit/>} label="Behavioral Flags" value={formatNumber(total)} description="Detected behavior events" accent="purple"/><KpiCard icon={<Activity/>} label="Behavior Types" value={formatNumber(list.length)} description="Detected categories" accent="blue"/><KpiCard icon={<AlertTriangle/>} label="High-Risk Trades" value={formatNumber(highRiskTrades.length)} description="High / critical risk view" accent="red"/><KpiCard icon={<Gauge/>} label="Source" value={dataSource === "tradingview" ? "CSV" : "DEMO"} description="Selected data source" accent="green"/></section><section className="two-column"><Panel title="Behavior Distribution" subtitle="Detected behavioral patterns" icon={<BrainCircuit size={18}/>}><div className="behavior-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={list} layout="vertical"><CartesianGrid stroke="#1e293b" horizontal={false}/><XAxis type="number" stroke="#64748b" fontSize={11}/><YAxis type="category" dataKey="behavior" stroke="#94a3b8" fontSize={11} width={110}/><Tooltip/><Bar dataKey="value" fill="#8b5cf6" radius={[0,5,5,0]}/></BarChart></ResponsiveContainer></div></Panel><Panel title="Behavior Interpretation" subtitle="Explainable rule engine" icon={<Activity size={18}/>}><div className="model-name"><div className="model-icon"><BrainCircuit size={21}/></div><div><strong>Behavior Detection Engine</strong><span>Evidence-based behavioral signals</span></div></div><div style={{marginTop:"18px",color:"#94a3b8",lineHeight:"1.7"}}>TradeMind uses measurable activity such as trading frequency, re-entry timing, position sizing and loss patterns to identify behavioral signals.</div></Panel></section><Panel title="Detected Patterns" subtitle="Current behavioral categories" icon={<Activity size={18}/>}><div className="metric-grid">{list.map(x=><Metric key={x.behavior} label={x.behavior} value={formatNumber(x.value)}/>)}</div></Panel></div>;
}

function MLPredictionsPage({
  mlMetrics,
  highRiskTrades,
  mlPredictions,
  dataSource,
}) {
  const m = mlMetrics?.metrics || {};
  const signals = mlPredictions?.length ? mlPredictions : highRiskTrades;

  return (
    <div className="dashboard-content">
      <section className="hero">
        <div>
          <div className="eyebrow">
            <Target size={14} /> MACHINE LEARNING
          </div>
          <h1>ML Predictions</h1>
          <p>Machine-learning model metrics and trade-level outcome signals.</p>
        </div>
        <div className="hero-status">
          <div className="hero-status-icon">
            <Target size={25} />
          </div>
          <div>
            <strong>ML Intelligence Active</strong>
            <span>
              {dataSource === "tradingview"
                ? "TradingView Paper predictions"
                : dataSource === "simulator" ? "No ML signals generated for demo trades yet" : "Historical model signals"}
            </span>
          </div>
        </div>
      </section>

{dataSource !== "simulator" && (
      <Panel
        title={mlMetrics?.model || "Trusted ML Model"}
        subtitle={mlMetrics?.validation || "Temporal validation"}
        icon={<Target size={18} />}
      >
        <div className="metric-grid">
          <Metric label="Accuracy" value={formatPercent(m.accuracy)} />
          <Metric label="Precision" value={formatPercent(m.precision)} />
          <Metric label="Recall" value={formatPercent(m.recall)} />
          <Metric label="F1 Score" value={formatPercent(m.f1)} />
          <Metric label="ROC-AUC" value={formatNumber(m.roc_auc)} />
          <Metric label="PR-AUC" value={formatNumber(m.pr_auc)} />
        </div>
      </Panel>

      )}
      <Panel
        title="Trade-Level ML Signals"
        subtitle={
          dataSource === "tradingview"
            ? "Generated from the imported TradingView Paper analysis"
            : dataSource === "simulator" ? "Demo journal trades do not have ML predictions yet" : "Generated from the historical TradeMind analysis"
        }
        icon={<TrendingUp size={18} />}
      >
        {signals.length > 0 ? (
          <div className="risk-table-wrapper">
            <table className="risk-table">
              <thead>
                <tr>
                  <th>TRADE</th>
                  <th>SYMBOL</th>
                  <th>DIRECTION</th>
                  <th>ML PROBABILITY</th>
                  <th>RISK</th>
                  <th>DECISION</th>
                </tr>
              </thead>
              <tbody>
                {signals.slice(0, 20).map((trade, index) => (
                  <tr key={trade.trade_id || trade.id || index}>
                    <td>
                      <strong className="trade-id">
                        {trade.trade_id || trade.id || "—"}
                      </strong>
                    </td>
                    <td>{trade.symbol || "—"}</td>
                    <td>{trade.direction || trade.side || "—"}</td>
                    <td>
                      {formatPercent(
                        trade.ml_win_probability ??
                          trade.win_probability ??
                          trade.predicted_probability
                      )}
                    </td>
                    <td>
                      <RiskBadge level={trade.risk_level || "UNKNOWN"} />
                    </td>
                    <td>
                      <DecisionBadge decision={trade.decision || "—"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState text="No ML prediction data available" />
        )}
      </Panel>
    </div>
  );
}

/* ============================================================
   KPI CARD
============================================================ */

function KpiCard({
  icon,
  label,
  value,
  description,
  accent,
}) {
  return (
    <div className={`kpi-card ${accent}`}>

      <div className="kpi-top">

        <div className="kpi-icon">
          {icon}
        </div>

        <div className="kpi-pulse">
          <span />
        </div>

      </div>

      <div className="kpi-label">
        {label}
      </div>

      <div className="kpi-value">
        {value}
      </div>

      <div className="kpi-description">
        {description}
      </div>

    </div>
  );
}

/* ============================================================
   PANEL
============================================================ */

function Panel({
  title,
  subtitle,
  icon,
  children,
  action,
}) {
  return (
    <div className="panel">

      <div className="panel-header">

        <div className="panel-title-group">

          <div className="panel-icon">
            {icon}
          </div>

          <div>

            <h2>
              {title}
            </h2>

            <p>
              {subtitle}
            </p>

          </div>

        </div>

        {action}

      </div>

      <div className="panel-body">
        {children}
      </div>

    </div>
  );
}

/* ============================================================
   LEGEND ITEM
============================================================ */

function LegendItem({
  color,
  label,
  value,
}) {
  return (
    <div className="legend-item">

      <span
        className="legend-dot"
        style={{
          background: color,
        }}
      />

      <span className="legend-label">
        {label}
      </span>

      <strong>
        {formatNumber(value)}
      </strong>

    </div>
  );
}

/* ============================================================
   METRIC
============================================================ */

function Metric({
  label,
  value,
}) {
  return (
    <div className="metric">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  );
}

/* ============================================================
   RISK BADGE
============================================================ */

function RiskBadge({
  level,
}) {
  return (
    <span
      className={`risk-badge ${String(
        level
      ).toLowerCase()}`}
    >
      {level}
    </span>
  );
}

/* ============================================================
   DECISION BADGE
============================================================ */

function DecisionBadge({
  decision,
}) {
  const className =
    decision === "ALLOW"
      ? "allow"
      : decision === "CAUTION"
      ? "caution"
      : decision === "DO NOT TRADE"
      ? "danger"
      : "warning";

  return (
    <span
      className={`decision-badge ${className}`}
    >
      {decision}
    </span>
  );
}

/* ============================================================
   EMPTY STATE
============================================================ */

function EmptyState({
  text,
}) {
  return (
    <div className="empty-state">

      <Activity size={22} />

      <span>
        {text}
      </span>

    </div>
  );
}

export default App;