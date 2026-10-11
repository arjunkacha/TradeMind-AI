import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  AlertTriangle,
  ShieldAlert,
  Activity,
  TrendingUp,
  RefreshCw,
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

const API = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API,
  timeout: 10000,
});

const riskColors = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

function formatNumber(value) {
  if (value === undefined || value === null) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}

function riskClass(level) {
  return String(level || "LOW")
    .toLowerCase()
    .replace(/\s+/g, "-");
}

function KpiCard({ icon, label, value, description, danger }) {
  return (
    <div className={`risk-kpi ${danger ? "danger" : ""}`}>
      <div className="risk-kpi-icon">
        {icon}
      </div>

      <div className="risk-kpi-content">
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{description}</small>
      </div>
    </div>
  );
}

function Panel({ title, subtitle, icon, children }) {
  return (
    <section className="risk-panel">
      <div className="risk-panel-header">
        <div className="risk-panel-title">
          <div className="risk-panel-icon">
            {icon}
          </div>

          <div>
            <h2>{title}</h2>
            <span>{subtitle}</span>
          </div>
        </div>
      </div>

      <div className="risk-panel-body">
        {children}
      </div>
    </section>
  );
}

export default function RiskIntelligence() {
  const [summary, setSummary] = useState(null);
  const [highRiskTrades, setHighRiskTrades] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const loadRiskIntelligence = async () => {
    try {
      setRefreshing(true);
      setError(null);

      const [summaryResponse, tradesResponse] =
        await Promise.all([
          api.get("/api/risk-summary"),
          api.get("/api/high-risk-trades?limit=15"),
        ]);

      setSummary(summaryResponse.data);

      setHighRiskTrades(
        Array.isArray(tradesResponse.data?.trades)
          ? tradesResponse.data.trades
          : []
      );
    } catch (err) {
      console.error(
        "Risk Intelligence API error:",
        err
      );

      setError(
        "Unable to load risk intelligence. Make sure the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadRiskIntelligence();
  }, []);

  const distribution = summary?.risk_distribution || {};

  const riskData = useMemo(
    () =>
      ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(
        (level) => ({
          name: level,
          value: Number(distribution[level] || 0),
        })
      ),
    [distribution]
  );

  const criticalCount =
    Number(distribution.CRITICAL || 0);

  const highCount =
    Number(distribution.HIGH || 0);

  const mediumCount =
    Number(distribution.MEDIUM || 0);

  const lowCount =
    Number(distribution.LOW || 0);

  const totalRiskTrades =
    lowCount +
    mediumCount +
    highCount +
    criticalCount;

  const exposureData = [
    {
      name: "LOW",
      value: lowCount,
    },
    {
      name: "MEDIUM",
      value: mediumCount,
    },
    {
      name: "HIGH",
      value: highCount,
    },
    {
      name: "CRITICAL",
      value: criticalCount,
    },
  ];

  if (loading) {
    return (
      <div className="risk-page">
        <div className="risk-loading">
          Loading Risk Intelligence...
        </div>
      </div>
    );
  }

  return (
    <div className="risk-page">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="risk-page-header">

        <div>
          <div className="eyebrow">
            <ShieldAlert size={14} />
            RISK INTELLIGENCE
          </div>

          <h1>Risk Intelligence</h1>

          <p>
            Understand portfolio risk exposure,
            behavioral risk and high-risk trades.
          </p>
        </div>

        <button
          className="risk-refresh-button"
          onClick={loadRiskIntelligence}
          disabled={refreshing}
        >
          <RefreshCw
            size={17}
            className={
              refreshing ? "risk-spin" : ""
            }
          />

          Refresh
        </button>

      </div>

      {/* =====================================================
          ERROR
      ===================================================== */}

      {error && (
        <div className="risk-error">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      {/* =====================================================
          KPI CARDS
      ===================================================== */}

      <section className="risk-kpi-grid">

        <KpiCard
          icon={<Activity size={19} />}
          label="Average Risk"
          value={formatNumber(
            summary?.average_risk_score
          )}
          description="Portfolio risk score / 100"
        />

        <KpiCard
          icon={<AlertTriangle size={19} />}
          label="Critical Trades"
          value={formatNumber(criticalCount)}
          description="Immediate attention required"
          danger={criticalCount > 0}
        />

        <KpiCard
          icon={<ShieldAlert size={19} />}
          label="High Risk"
          value={formatNumber(highCount)}
          description="High behavioral risk"
          danger={highCount > 0}
        />

        <KpiCard
          icon={<TrendingUp size={19} />}
          label="Analyzed Trades"
          value={formatNumber(totalRiskTrades)}
          description="Risk-classified trades"
        />

      </section>

      {/* =====================================================
          CHARTS
      ===================================================== */}

      <section className="risk-two-column">

        {/* RISK DISTRIBUTION */}

        <Panel
          title="Risk Distribution"
          subtitle="Portfolio behavioral risk"
          icon={<ShieldAlert size={18} />}
        >

          <div className="risk-chart-container">

            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <PieChart>

                <Pie
                  data={riskData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={75}
                  outerRadius={110}
                  paddingAngle={3}
                  stroke="none"
                >
                  {riskData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={
                        riskColors[entry.name]
                      }
                    />
                  ))}
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

            <div className="risk-chart-center">
              <strong>
                {formatNumber(totalRiskTrades)}
              </strong>

              <span>TRADES</span>
            </div>

          </div>

          <div className="risk-legend">

            {riskData.map((item) => (
              <div
                className="risk-legend-item"
                key={item.name}
              >
                <span>
                  <i
                    style={{
                      background:
                        riskColors[item.name],
                    }}
                  />
                  {item.name}
                </span>

                <strong>
                  {formatNumber(item.value)}
                </strong>
              </div>
            ))}

          </div>

        </Panel>

        {/* EXPOSURE BAR CHART */}

        <Panel
          title="Risk Exposure"
          subtitle="Number of trades by risk level"
          icon={<Activity size={18} />}
        >

          <div className="risk-bar-container">

            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <BarChart
                data={exposureData}
                margin={{
                  top: 10,
                  right: 10,
                  left: 0,
                  bottom: 5,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#1e293b"
                />

                <XAxis
                  dataKey="name"
                  stroke="#64748b"
                />

                <YAxis
                  stroke="#64748b"
                />

                <Tooltip
                  contentStyle={{
                    background: "#111827",
                    border:
                      "1px solid #263247",
                    borderRadius: "10px",
                    color: "#fff",
                  }}
                />

                <Bar
                  dataKey="value"
                  radius={[6, 6, 0, 0]}
                >
                  {exposureData.map(
                    (entry) => (
                      <Cell
                        key={entry.name}
                        fill={
                          riskColors[
                            entry.name
                          ]
                        }
                      />
                    )
                  )}
                </Bar>

              </BarChart>
            </ResponsiveContainer>

          </div>

        </Panel>

      </section>

      {/* =====================================================
          HIGH RISK TRADES
      ===================================================== */}

      <Panel
        title="Highest Risk Trades"
        subtitle="Trades requiring the most attention"
        icon={<AlertTriangle size={18} />}
      >

        {highRiskTrades.length === 0 ? (

          <div className="risk-empty">
            No high-risk trades detected.
          </div>

        ) : (

          <div className="risk-table-wrapper">

            <table className="risk-table">

              <thead>
                <tr>
                  <th>Trade</th>
                  <th>Symbol</th>
                  <th>Direction</th>
                  <th>Risk Score</th>
                  <th>Risk Level</th>
                  <th>Decision</th>
                </tr>
              </thead>

              <tbody>

                {highRiskTrades.map(
                  (trade) => {

                    const level =
                      trade.risk_level ||
                      "HIGH";

                    return (
                      <tr
                        key={
                          trade.trade_id
                        }
                      >

                        <td>
                          <strong>
                            {trade.trade_id}
                          </strong>
                        </td>

                        <td>
                          {trade.symbol || "—"}
                        </td>

                        <td>
                          {trade.direction || "—"}
                        </td>

                        <td>
                          <strong>
                            {formatNumber(
                              trade.risk_score
                            )}
                          </strong>
                        </td>

                        <td>
                          <span
                            className={`risk-level-badge ${riskClass(
                              level
                            )}`}
                          >
                            {level}
                          </span>
                        </td>

                        <td>
                          {trade.decision ||
                            "—"}
                        </td>

                      </tr>
                    );
                  }
                )}

              </tbody>

            </table>

          </div>

        )}

      </Panel>

      {/* =====================================================
          INTELLIGENCE SUMMARY
      ===================================================== */}

      <section className="risk-intelligence-card">

        <div className="risk-intelligence-icon">
          <ShieldAlert size={23} />
        </div>

        <div>

          <div className="eyebrow">
            AI RISK ASSESSMENT
          </div>

          <h2>Portfolio Risk Assessment</h2>

          <p>

            TradeMind has classified{" "}
            <strong>
              {formatNumber(criticalCount)}
            </strong>{" "}
            trades as critical and{" "}
            <strong>
              {formatNumber(highCount)}
            </strong>{" "}
            trades as high risk.

            {" "}

            {criticalCount > 0
              ? "Critical-risk trades require immediate attention and should be reviewed before execution."
              : "No critical-risk trades are currently present."}

          </p>

          <div className="risk-recommendation">

            <strong>
              Recommended Action
            </strong>

            <span>
              Prioritize critical and high-risk
              trades for behavioral review and
              apply strict position-risk controls.
            </span>

          </div>

        </div>

      </section>

    </div>
  );
}