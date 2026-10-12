
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronRight,
  LockKeyhole,
  Menu,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import { useState } from "react";
import "./landing.css";

const features = [
  {
    icon: BrainCircuit,
    title: "AI Trade Intelligence",
    description:
      "Analyze your trading decisions with ML-powered signals and structured trade insights.",
    tag: "INTELLIGENCE",
  },
  {
    icon: ShieldCheck,
    title: "Risk Intelligence",
    description:
      "Understand risk exposure, identify risky patterns, and make more disciplined decisions.",
    tag: "RISK MANAGEMENT",
  },
  {
    icon: Activity,
    title: "Behavior Analytics",
    description:
      "Recognize overtrading, rapid re-entry, and other patterns in your trading behavior.",
    tag: "DISCIPLINE",
  },
  {
    icon: ChartNoAxesCombined,
    title: "Performance Dashboard",
    description:
      "Review trade outcomes, performance metrics, and historical activity in one place.",
    tag: "ANALYTICS",
  },
];

const steps = [
  {
    number: "01",
    title: "Create your account",
    description: "Sign up to get your own demo trading workspace.",
  },
  {
    number: "02",
    title: "Analyze your trades",
    description: "Explore trade history, risk indicators, and behavioral insights.",
  },
  {
    number: "03",
    title: "Learn and improve",
    description: "Use the insights as a guide to review your trading decisions.",
  },
];

function Brand() {
  return (
    <a className="tm-brand" href="/" aria-label="TradeMind AI home">
      <span className="tm-brand-icon">
        <BrainCircuit size={23} />
      </span>
      <span>
        <strong>TradeMind<span>-AI</span></strong>
        <small>TRADING INTELLIGENCE</small>
      </span>
    </a>
  );
}

function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="landing">
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <Brand />

          <button
            className="mobile-menu-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            aria-controls="landing-navigation"
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>

          <nav
            id="landing-navigation"
            className={menuOpen ? "landing-links open" : "landing-links"}
          >
            <a href="#features" onClick={() => setMenuOpen(false)}>Features</a>
            <a href="#how-it-works" onClick={() => setMenuOpen(false)}>How it works</a>
            <a href="#about" onClick={() => setMenuOpen(false)}>About</a>
            <a className="nav-login" href="/login">Log in</a>
            <a className="nav-signup" href="/signup">
              Get started <ArrowRight size={16} />
            </a>
          </nav>
        </div>
      </header>

      <main>
        <section className="hero-section">
          <div className="hero-glow hero-glow-one" />
          <div className="hero-glow hero-glow-two" />

          <div className="hero-content">
            <div className="hero-badge">
              <Sparkles size={14} />
              Trading analytics. Built around discipline.
            </div>

            <h1>
              Your trades tell a story.
              <span> Learn to read it.</span>
            </h1>

            <p className="hero-description">
              TradeMind-AI helps you review trading performance, understand
              risk, and identify behavioral patterns through one intelligent
              trading workspace.
            </p>

            <div className="hero-actions">
              <a className="button-primary" href="/signup">
                Get started for free <ArrowRight size={18} />
              </a>
              <a className="button-secondary" href="#features">
                Explore features <ChevronRight size={18} />
              </a>
            </div>

            <div className="hero-trust">
              <span><CheckCircle2 size={15} /> Personal demo workspace</span>
              <span><CheckCircle2 size={15} /> Risk-focused insights</span>
            </div>
          </div>

          <div className="hero-visual" aria-label="Illustrative trading analytics dashboard">
            <div className="preview-window">
              <div className="preview-topbar">
                <div className="preview-dots"><i /><i /><i /></div>
                <span>TRADEMIND / OVERVIEW</span>
                <span className="preview-live"><i /> DEMO PREVIEW</span>
              </div>

              <div className="preview-body">
                <aside className="preview-sidebar">
                  <div className="preview-mark"><BrainCircuit size={19} /></div>
                  <span className="selected"><Activity size={17} /></span>
                  <span><ChartNoAxesCombined size={17} /></span>
                  <span><ShieldCheck size={17} /></span>
                  <span><Target size={17} /></span>
                </aside>

                <div className="preview-main">
                  <div className="preview-heading">
                    <div>
                      <small>YOUR WORKSPACE</small>
                      <h3>Trading overview</h3>
                    </div>
                    <span className="preview-chip">Sample UI</span>
                  </div>

                  <div className="preview-stats">
                    <div><small>Trade analysis</small><strong>Detailed</strong><span>Historical review</span></div>
                    <div><small>Risk insights</small><strong>Enabled</strong><span>Risk awareness</span></div>
                    <div><small>Behavior review</small><strong>Available</strong><span>Pattern detection</span></div>
                  </div>

                  <div className="preview-chart-card">
                    <div className="preview-chart-heading">
                      <div><small>PERFORMANCE REVIEW</small><strong>Trading activity</strong></div>
                      <span>Illustrative</span>
                    </div>
                    <svg viewBox="0 0 540 150" role="img" aria-label="Illustrative performance line chart">
                      <defs>
                        <linearGradient id="tmArea" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#a78bfa" stopOpacity=".28" />
                          <stop offset="100%" stopColor="#a78bfa" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      {[25, 60, 95, 130].map((y) => (
                        <line key={y} x1="0" y1={y} x2="540" y2={y} stroke="#263146" strokeDasharray="4 5" />
                      ))}
                      <path d="M0 115 L42 102 L80 110 L120 74 L160 88 L205 61 L246 78 L287 45 L326 61 L367 33 L408 50 L452 22 L495 38 L540 12 L540 150 L0 150 Z" fill="url(#tmArea)" />
                      <path d="M0 115 L42 102 L80 110 L120 74 L160 88 L205 61 L246 78 L287 45 L326 61 L367 33 L408 50 L452 22 L495 38 L540 12" fill="none" stroke="#a78bfa" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <div className="preview-chart-legend"><span><i /> Illustrative trend</span><span>Not live trading data</span></div>
                  </div>

                  <div className="preview-bottom">
                    <div><span className="preview-icon purple"><BrainCircuit size={17} /></span><span><small>AI INSIGHTS</small><strong>Review your decisions</strong></span></div>
                    <div><span className="preview-icon green"><ShieldCheck size={17} /></span><span><small>RISK REVIEW</small><strong>Understand your exposure</strong></span></div>
                  </div>
                </div>
              </div>
            </div>
            <div className="floating-note"><span><Zap size={16} /></span><div><strong>Insight-led trading</strong><small>Review. Learn. Improve.</small></div></div>
          </div>

          <div className="hero-bottom-line">
            <span>ANALYZE WITH CLARITY</span>
            <span>UNDERSTAND YOUR RISK</span>
            <span>BUILD BETTER HABITS</span>
          </div>
        </section>

        <section className="features-section" id="features">
          <div className="section-heading">
            <span className="eyebrow">ONE WORKSPACE. MORE CLARITY.</span>
            <h2>Understand more than your P&amp;L.</h2>
            <p>
              Look beyond individual wins and losses. Build a clearer picture
              of how you trade, where risk appears, and what deserves review.
            </p>
          </div>

          <div className="feature-grid">
            {features.map(({ icon: Icon, title, description, tag }) => (
              <article className="feature-card" key={title}>
                <div className="feature-card-top">
                  <span className="feature-icon"><Icon size={22} /></span>
                  <span className="feature-tag">{tag}</span>
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
                <a href="/signup">Explore workspace <ArrowRight size={15} /></a>
              </article>
            ))}
          </div>
        </section>

        <section className="how-section" id="how-it-works">
          <div className="section-heading">
            <span className="eyebrow">GET STARTED IN THREE STEPS</span>
            <h2>A clearer trading review starts here.</h2>
          </div>

          <div className="steps-grid">
            {steps.map((step) => (
              <article className="step-card" key={step.number}>
                <span className="step-number">{step.number}</span>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="cta-section" id="about">
          <div className="cta-glow" />
          <div className="cta-content">
            <span className="eyebrow"><LockKeyhole size={14} /> YOUR OWN WORKSPACE</span>
            <h2>Make every trade a chance to learn.</h2>
            <p>Create your account to explore your own demo trading workspace and review your trading decisions.</p>
            <a className="button-primary" href="/signup">
              Create your account <ArrowRight size={18} />
            </a>
            <small>Demo analytics are for educational purposes and do not guarantee trading results.</small>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <Brand />
        <p>Trading intelligence for more informed decisions.</p>
        <span>© {new Date().getFullYear()} TradeMind-AI</span>
      </footer>
    </div>
  );
}

export default LandingPage;
