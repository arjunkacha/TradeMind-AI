import { useEffect, useMemo, useState } from "react";
import "./TradeAnalysis.css";

const API_URL = "http://127.0.0.1:8000";

const PAGE_SIZE = 25;

function riskClass(level) {
  if (!level) return "neutral";

  switch (String(level).toUpperCase()) {
    case "CRITICAL":
      return "critical";
    case "HIGH":
      return "high";
    case "MEDIUM":
      return "medium";
    case "LOW":
      return "low";
    default:
      return "neutral";
  }
}

function normalizeRisk(trade) {
  return (
    trade?.risk_level ||
    trade?.riskLevel ||
    "LOW"
  );
}

function normalizeDirection(trade) {
  return String(trade?.direction || "").toUpperCase();
}

function normalizeDecision(trade) {
  return String(trade?.decision || "").toUpperCase();
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toFixed(decimals);
}

function formatProbability(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  // Backend stores ML probability as 0–1.
  return `${(number * 100).toFixed(2)}%`;
}

function TradeAnalysis({ source = "historical" }) {
  const [trades, setTrades] = useState([]);
  const [selectedTrade, setSelectedTrade] = useState(null);

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [directionFilter, setDirectionFilter] = useState("ALL");
  const [decisionFilter, setDecisionFilter] = useState("ALL");

  const [currentPage, setCurrentPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadTrades();
  }, [source]);

  /*
   * Load all trades from FastAPI.
   */
  const loadTrades = async () => {
    try {
      setLoading(true);
      setError("");

      const endpoint =
        source === "tradingview"
          ? "/api/tradingview/trades"
          : "/api/trades";

      const response = await fetch(
        `${API_URL}${endpoint}`
      );

      if (!response.ok) {
        throw new Error(
          `Unable to load trades (${response.status})`
        );
      }

      const data = await response.json();

      // API may return:
      // 1. [...]
      // 2. { trades: [...] }
      // 3. { data: [...] }
      const tradeList = Array.isArray(data)
        ? data
        : Array.isArray(data?.trades)
        ? data.trades
        : Array.isArray(data?.data)
        ? data.data
        : [];

      setTrades(tradeList);

      // Keep current page valid after refresh.
      setCurrentPage(1);
    } catch (err) {
      console.error("Trade loading error:", err);
      setError(err.message || "Unable to load trades.");
      setTrades([]);
    } finally {
      setLoading(false);
    }
  };

  /*
   * Load complete AI analysis for one trade.
   */
  const openTrade = async (tradeId) => {
    try {
      setDetailLoading(true);
      setError("");

      const endpoint =
        source === "tradingview"
          ? `/api/tradingview/trades/${encodeURIComponent(
              tradeId
            )}`
          : `/api/trades/${encodeURIComponent(
              tradeId
            )}`;

      const response = await fetch(
        `${API_URL}${endpoint}`
      );

      if (!response.ok) {
        throw new Error(
          `Unable to load trade details (${response.status})`
        );
      }

      const data = await response.json();

      setSelectedTrade(data?.trade || data);
    } catch (err) {
      console.error("Trade detail error:", err);
      setError(
        err.message || "Unable to load trade details."
      );
    } finally {
      setDetailLoading(false);
    }
  };

  /*
   * Filter trades.
   */
  const filteredTrades = useMemo(() => {
    const query = search.trim().toLowerCase();

    return trades.filter((trade) => {
      const matchesSearch =
        !query ||
        String(trade?.trade_id || "")
          .toLowerCase()
          .includes(query) ||
        String(trade?.symbol || "")
          .toLowerCase()
          .includes(query) ||
        String(trade?.account || "")
          .toLowerCase()
          .includes(query) ||
        String(trade?.decision || "")
          .toLowerCase()
          .includes(query);

      const matchesRisk =
        riskFilter === "ALL" ||
        normalizeRisk(trade).toUpperCase() === riskFilter;

      const matchesDirection =
        directionFilter === "ALL" ||
        normalizeDirection(trade) === directionFilter;

      const matchesDecision =
        decisionFilter === "ALL" ||
        normalizeDecision(trade) === decisionFilter;

      return (
        matchesSearch &&
        matchesRisk &&
        matchesDirection &&
        matchesDecision
      );
    });
  }, [
    trades,
    search,
    riskFilter,
    directionFilter,
    decisionFilter,
  ]);

  /*
   * Pagination.
   */
  const totalPages = Math.max(
    1,
    Math.ceil(filteredTrades.length / PAGE_SIZE)
  );

  const safeCurrentPage = Math.min(
    currentPage,
    totalPages
  );

  const pageStart =
    (safeCurrentPage - 1) * PAGE_SIZE;

  const paginatedTrades = filteredTrades.slice(
    pageStart,
    pageStart + PAGE_SIZE
  );

  /*
   * Reset pagination whenever filters/search change.
   */
  useEffect(() => {
    setCurrentPage(1);
  }, [
    search,
    riskFilter,
    directionFilter,
    decisionFilter,
  ]);

  /*
   * Available filter values.
   */
  const availableDirections = useMemo(() => {
    const values = new Set();

    trades.forEach((trade) => {
      const direction = normalizeDirection(trade);

      if (direction) {
        values.add(direction);
      }
    });

    return Array.from(values).sort();
  }, [trades]);

  const availableDecisions = useMemo(() => {
    const values = new Set();

    trades.forEach((trade) => {
      const decision = normalizeDecision(trade);

      if (decision) {
        values.add(decision);
      }
    });

    return Array.from(values).sort();
  }, [trades]);

  const clearFilters = () => {
    setSearch("");
    setRiskFilter("ALL");
    setDirectionFilter("ALL");
    setDecisionFilter("ALL");
    setCurrentPage(1);
  };

  const hasActiveFilters =
    search ||
    riskFilter !== "ALL" ||
    directionFilter !== "ALL" ||
    decisionFilter !== "ALL";

  return (
    <div className="trade-analysis-page">

      {/* =====================================================
          PAGE HEADER
      ====================================================== */}
      <div className="page-header">

        <div>
          <div className="eyebrow">
            TRADE INTELLIGENCE
          </div>

          <h1>Trade Analysis</h1>

          <p>
            Analyze individual trades, behavioral patterns
            and AI risk decisions.
          </p>
        </div>

        <button
          className="refresh-btn"
          onClick={loadTrades}
          disabled={loading}
        >
          {loading ? "↻ Loading..." : "↻ Refresh"}
        </button>

      </div>


      {/* =====================================================
          TOOLBAR
      ====================================================== */}
      <div className="analysis-toolbar">

        <div className="search-box">
          <span>⌕</span>

          <input
            type="text"
            placeholder="Search Trade ID, symbol, account or decision..."
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
          />
        </div>


        <select
          value={riskFilter}
          onChange={(e) =>
            setRiskFilter(e.target.value)
          }
        >
          <option value="ALL">
            All Risk Levels
          </option>

          <option value="LOW">
            Low Risk
          </option>

          <option value="MEDIUM">
            Medium Risk
          </option>

          <option value="HIGH">
            High Risk
          </option>

          <option value="CRITICAL">
            Critical Risk
          </option>
        </select>


        <select
          value={directionFilter}
          onChange={(e) =>
            setDirectionFilter(e.target.value)
          }
        >
          <option value="ALL">
            All Directions
          </option>

          {availableDirections.map((direction) => (
            <option
              value={direction}
              key={direction}
            >
              {direction}
            </option>
          ))}
        </select>


        <select
          value={decisionFilter}
          onChange={(e) =>
            setDecisionFilter(e.target.value)
          }
        >
          <option value="ALL">
            All Decisions
          </option>

          {availableDecisions.map((decision) => (
            <option
              value={decision}
              key={decision}
            >
              {decision}
            </option>
          ))}
        </select>


        {hasActiveFilters && (
          <button
            className="clear-filter-btn"
            onClick={clearFilters}
          >
            Clear
          </button>
        )}


        <div className="trade-count">
          {filteredTrades.length.toLocaleString()} trades
        </div>

      </div>


      {/* =====================================================
          ERROR
      ====================================================== */}
      {error && (
        <div className="error-banner">
          ⚠ {error}
        </div>
      )}


      {/* =====================================================
          MAIN CONTENT
      ====================================================== */}
      <div className="analysis-grid">

        {/* ===================================================
            TRADE TABLE
        ==================================================== */}
        <div className="panel trades-panel">

          <div className="panel-header">

            <div>
              <h2>Trade Intelligence</h2>

              <span>
                AI-analyzed trading activity
              </span>
            </div>

            <div className="panel-meta">
              {filteredTrades.length > 0
                ? `${pageStart + 1}–${Math.min(
                    pageStart + PAGE_SIZE,
                    filteredTrades.length
                  )}`
                : "0"}
            </div>

          </div>


          {loading ? (

            <div className="loading">
              Loading trades...
            </div>

          ) : filteredTrades.length === 0 ? (

            <div className="empty-state">

              <div className="placeholder-icon">
                ◌
              </div>

              <h3>No trades found</h3>

              <p>
                No trades match your current search
                and filter criteria.
              </p>

              {hasActiveFilters && (
                <button
                  className="view-btn"
                  onClick={clearFilters}
                >
                  Clear Filters
                </button>
              )}

            </div>

          ) : (

            <>

              <div className="table-wrapper">

                <table>

                  <thead>
                    <tr>
                      <th>Trade</th>
                      <th>Symbol</th>
                      <th>Direction</th>
                      <th>Risk</th>
                      <th>Decision</th>
                      <th></th>
                    </tr>
                  </thead>


                  <tbody>

                    {paginatedTrades.map((trade) => {

                      const level =
                        normalizeRisk(trade);

                      const tradeId =
                        trade?.trade_id ||
                        trade?.tradeId ||
                        "—";

                      const isSelected =
                        selectedTrade?.trade_id ===
                        tradeId;

                      return (
                        <tr
                          key={tradeId}
                          className={
                            isSelected
                              ? "selected-trade"
                              : ""
                          }
                        >

                          <td>
                            <strong>
                              {tradeId}
                            </strong>
                          </td>


                          <td>
                            {trade?.symbol || "—"}
                          </td>


                          <td>
                            <span
                              className={`direction ${String(
                                trade?.direction || ""
                              ).toLowerCase()}`}
                            >
                              {trade?.direction || "—"}
                            </span>
                          </td>


                          <td>
                            <span
                              className={`risk-badge ${riskClass(
                                level
                              )}`}
                            >
                              {level}
                            </span>
                          </td>


                          <td>
                            <span
                              className={`decision-text ${String(
                                trade?.decision || ""
                              )
                                .toLowerCase()
                                .replace(
                                  /\s+/g,
                                  "-"
                                )}`}
                            >
                              {trade?.decision || "—"}
                            </span>
                          </td>


                          <td>

                            <button
                              className="view-btn"
                              onClick={() =>
                                openTrade(tradeId)
                              }
                              disabled={
                                detailLoading &&
                                selectedTrade?.trade_id ===
                                  tradeId
                              }
                            >
                              {detailLoading &&
                              selectedTrade?.trade_id ===
                                tradeId
                                ? "Loading..."
                                : "View →"}
                            </button>

                          </td>

                        </tr>
                      );
                    })}

                  </tbody>

                </table>

              </div>


              {/* =================================================
                  PAGINATION
              ================================================== */}
              {totalPages > 1 && (

                <div className="pagination">

                  <button
                    className="pagination-btn"
                    disabled={safeCurrentPage === 1}
                    onClick={() =>
                      setCurrentPage(
                        safeCurrentPage - 1
                      )
                    }
                  >
                    ← Previous
                  </button>


                  <div className="pagination-info">
                    Page{" "}
                    <strong>
                      {safeCurrentPage}
                    </strong>{" "}
                    of{" "}
                    <strong>
                      {totalPages}
                    </strong>
                  </div>


                  <button
                    className="pagination-btn"
                    disabled={
                      safeCurrentPage === totalPages
                    }
                    onClick={() =>
                      setCurrentPage(
                        safeCurrentPage + 1
                      )
                    }
                  >
                    Next →
                  </button>

                </div>

              )}

            </>

          )}

        </div>


        {/* ===================================================
            DETAIL PANEL
        ==================================================== */}
        <div className="panel detail-panel">

          {detailLoading ? (

            <div className="detail-placeholder">

              <div className="placeholder-icon">
                ◌
              </div>

              <h2>
                Loading Trade Intelligence
              </h2>

              <p>
                TradeMind AI is analyzing the
                selected trade.
              </p>

            </div>

          ) : !selectedTrade ? (

            <div className="detail-placeholder">

              <div className="placeholder-icon">
                ◉
              </div>

              <h2>Select a trade</h2>

              <p>
                Select a trade from the intelligence
                table to inspect its complete AI
                analysis.
              </p>

            </div>

          ) : (

            <TradeDetails
              trade={selectedTrade}
            />

          )}

        </div>

      </div>

    </div>
  );
}


/* ============================================================
   TRADE DETAILS
============================================================ */

function TradeDetails({ trade }) {

  const riskLevel =
    trade?.risk_level ||
    trade?.riskLevel ||
    "UNKNOWN";


  const behaviors =
    trade?.behaviors ||
    trade?.behavior_flags ||
    trade?.behaviorFlags ||
    [];


  const behaviorList = Array.isArray(behaviors)
    ? behaviors
    : String(behaviors)
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);


  const mlProbability =
    trade?.ml_win_probability ??
    trade?.mlWinProbability;


  const riskScore =
    trade?.risk_score ??
    trade?.riskScore;


  const disciplineScore =
    trade?.discipline_score ??
    trade?.disciplineScore;


  const decision =
    trade?.decision ||
    "NO DECISION";


  const decisionReason =
    trade?.reason ||
    trade?.decision_reason ||
    trade?.decisionReason ||
    "No decision explanation available.";


  const recommendation =
    trade?.recommendation ||
    trade?.recommended_action ||
    trade?.recommendedAction ||
    "Review trading conditions";


  const outcomeSignal =
    trade?.outcome_signal ||
    trade?.outcomeSignal ||
    "TradeMind recommendation generated from risk and behavioral analysis.";


  return (

    <div className="trade-details">

      {/* =====================================================
          TRADE HEADING
      ====================================================== */}
      <div className="detail-heading">

        <div>

          <div className="eyebrow">
            TRADE ANALYSIS
          </div>

          <h2>
            {trade?.trade_id || "Unknown Trade"}
          </h2>

          <span>
            {trade?.symbol || "Unknown Symbol"}
            {trade?.direction
              ? ` • ${trade.direction}`
              : ""}
          </span>

        </div>


        <span
          className={`risk-badge large ${riskClass(
            riskLevel
          )}`}
        >
          {riskLevel}
        </span>

      </div>


      {/* =====================================================
          METRICS
      ====================================================== */}
      <div className="detail-metrics">

        <Metric
          label="Risk Score"
          value={formatNumber(riskScore)}
        />


        <Metric
          label="Discipline"
          value={formatNumber(
            disciplineScore
          )}
        />


        <Metric
          label="ML Win Probability"
          value={formatProbability(
            mlProbability
          )}
        />


        <Metric
          label="Direction"
          value={
            trade?.direction || "—"
          }
        />

      </div>


      {/* =====================================================
          DECISION
      ====================================================== */}
      <div className="decision-card">

        <div className="decision-label">
          TRADEMIND DECISION
        </div>

        <div className="decision-value">
          {decision}
        </div>

        <p>
          {decisionReason}
        </p>

      </div>


      {/* =====================================================
          TRADE INFORMATION
      ====================================================== */}
      <div className="detail-section">

        <div className="section-title">
          Trade Information
        </div>


        <div className="trade-info-grid">

          <InfoRow
            label="Trade ID"
            value={trade?.trade_id}
          />

          <InfoRow
            label="Symbol"
            value={trade?.symbol}
          />

          <InfoRow
            label="Direction"
            value={trade?.direction}
          />

          <InfoRow
            label="Account"
            value={trade?.account}
          />

          <InfoRow
            label="Entry Time"
            value={
              trade?.entry_time ||
              trade?.entryTime
            }
          />

          <InfoRow
            label="Risk Level"
            value={riskLevel}
          />

        </div>

      </div>


      {/* =====================================================
          BEHAVIORS
      ====================================================== */}
      <div className="detail-section">

        <div className="section-title">
          Detected Behaviors
        </div>


        <div className="behavior-list">

          {behaviorList.length ? (

            behaviorList.map(
              (behavior, index) => (

                <div
                  className="behavior-item"
                  key={`${behavior}-${index}`}
                >

                  <span className="behavior-dot" />

                  {behavior}

                </div>

              )
            )

          ) : (

            <div className="muted">
              No behavioral flags detected.
            </div>

          )}

        </div>

      </div>


      {/* =====================================================
          AI RECOMMENDATION
      ====================================================== */}
      <div className="detail-section">

        <div className="section-title">
          AI Recommendation
        </div>


        <div className="recommendation">

          <div className="recommendation-icon">
            ✦
          </div>


          <div>

            <strong>
              {recommendation}
            </strong>

            <p>
              {outcomeSignal}
            </p>

          </div>

        </div>

      </div>

    </div>
  );
}


/* ============================================================
   METRIC
============================================================ */

function Metric({ label, value }) {

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
   INFO ROW
============================================================ */

function InfoRow({ label, value }) {

  return (

    <div className="info-row">

      <span>
        {label}
      </span>

      <strong>
        {value || "—"}
      </strong>

    </div>
  );
}


export default TradeAnalysis;