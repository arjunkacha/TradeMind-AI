import { useState } from "react";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Eye,
  EyeOff,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import api from "./lib/api";
import "./AuthPage.css";

export default function AuthPage({ mode = "login" }) {
  const isSignup = mode === "signup";
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (isSignup && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (isSignup && password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);
    try {
      // The current backend signup schema stores email/password only.
      // Profile fields are collected in this UI but need a backend schema/database
      // update before they can be saved to the user's account.
      const response = await api.post(
        `/api/auth/${isSignup ? "signup" : "login"}`,
        { email: email.trim(), password }
      );
      const token = response.data?.access_token;
      if (!token) throw new Error("The server did not return an access token.");
      localStorage.setItem("trademind_access_token", token);
      window.location.assign("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : err.message || "Unable to connect. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleSignup() {
    setError("Google sign-up is not configured yet. Please use email and password.");
  }

  return (
    <main className={`auth-page ${isSignup ? "auth-page-signup" : "auth-page-login"}`}>
      <div className="auth-orb auth-orb-one" aria-hidden="true" />
      <div className="auth-orb auth-orb-two" aria-hidden="true" />

      <a className="auth-home-brand" href="/" aria-label="TradeMind AI home">
        <span className="auth-brand-icon"><BrainCircuit size={23} /></span>
        <span className="auth-brand-copy">
          <strong>TradeMind<span>-AI</span></strong>
          <small>TRADING INTELLIGENCE</small>
        </span>
      </a>

      {isSignup ? (
        <section className="signup-card" aria-labelledby="signup-title">
          <h1 id="signup-title">Sign up</h1>
          <form onSubmit={handleSubmit}>
            <div className="signup-name-row">
              <input
                aria-label="First name"
                autoComplete="given-name"
                placeholder="First name"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                maxLength={80}
                required
              />
              <input
                aria-label="Last name"
                autoComplete="family-name"
                placeholder="Last name"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                maxLength={80}
                required
              />
            </div>
            <input
              aria-label="Email"
              type="email"
              autoComplete="email"
              placeholder="Email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              maxLength={254}
              required
            />
            <input
              aria-label="Birth date"
              type="text"
              onFocus={(event) => { event.currentTarget.type = "date"; }}
              onBlur={(event) => { if (!event.currentTarget.value) event.currentTarget.type = "text"; }}
              autoComplete="bday"
              placeholder="Birth date"
              value={birthDate}
              onChange={(event) => setBirthDate(event.target.value)}
              required
            />
            <input
              aria-label="Phone number"
              type="tel"
              autoComplete="tel"
              placeholder="Phone number"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              maxLength={25}
              required
            />
            <div className="signup-password-wrap">
              <input
                aria-label="Password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                placeholder="Password"
                minLength={8}
                maxLength={128}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button
                type="button"
                className="signup-password-toggle"
                onClick={() => setShowPassword((shown) => !shown)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            <div className="signup-password-wrap">
              <input
                aria-label="Confirm password"
                type={showConfirmPassword ? "text" : "password"}
                autoComplete="new-password"
                placeholder="Confirm password"
                minLength={8}
                maxLength={128}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
              <button
                type="button"
                className="signup-password-toggle"
                onClick={() => setShowConfirmPassword((shown) => !shown)}
                aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
              >
                {showConfirmPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>

            {error && <p className="auth-error signup-message" role="alert">{error}</p>}
            {notice && <p className="signup-message" role="status">{notice}</p>}

            <button className="signup-submit" type="submit" disabled={loading}>
              {loading ? "Creating account..." : "Sign Up"}
            </button>
          </form>

          <p className="signup-switch">Already have an account? <a href="/login">Log In</a></p>
          <div className="signup-or"><span>or</span></div>
          <button className="signup-google" type="button" onClick={handleGoogleSignup}>
            <span className="google-g" aria-hidden="true">G</span>
            Sign up with Google
          </button>
          <a className="signup-back" href="/">← Back to home</a>
          <p className="signup-privacy"><ShieldCheck size={13} /> Your trading workspace stays personal.</p>
        </section>
      ) : (
        <div className="auth-layout">
          <section className="auth-story">
            <div className="auth-story-badge"><Sparkles size={14} /> TRADING ANALYTICS. BUILT AROUND DISCIPLINE.</div>
            <h1>Trade with awareness.<span> Learn from every decision.</span></h1>
            <p className="auth-story-description">Your personal workspace to review performance, understand risk, and recognize the habits behind your trading decisions.</p>
            <div className="auth-benefits">
              <div><span className="auth-benefit-icon"><Activity size={18} /></span><span><strong>Behavioral insights</strong><small>Spot patterns in your trading activity.</small></span></div>
              <div><span className="auth-benefit-icon"><ShieldCheck size={18} /></span><span><strong>Risk awareness</strong><small>Review risk before building better habits.</small></span></div>
              <div><span className="auth-benefit-icon"><CheckCircle2 size={18} /></span><span><strong>Your own workspace</strong><small>Keep your account experience personal.</small></span></div>
            </div>
            <p className="auth-story-footnote">Demo analytics are educational tools and do not guarantee trading results.</p>
          </section>

          <section className="auth-card">
            <div className="auth-card-heading"><span className="auth-card-icon"><BrainCircuit size={20} /></span><span className="auth-card-kicker">WELCOME BACK</span></div>
            <h2>Sign in to TradeMind</h2>
            <p className="auth-description">Enter your credentials to continue to your workspace.</p>
            <form onSubmit={handleSubmit}>
              <label htmlFor="auth-email">Email address</label>
              <input id="auth-email" type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} maxLength={254} required />
              <div className="auth-password-label"><label htmlFor="auth-password">Password</label><span>Welcome back</span></div>
              <div className="auth-password-wrap">
                <input id="auth-password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter your password" maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} required />
                <button type="button" className="auth-password-toggle" onClick={() => setShowPassword((shown) => !shown)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button>
              </div>
              {error && <p className="auth-error" role="alert">{error}</p>}
              <button className="auth-submit" type="submit" disabled={loading}><span>{loading ? "Please wait..." : "Sign in"}</span>{!loading && <ArrowRight size={17} />}</button>
            </form>
            <p className="auth-switch">New to TradeMind-AI? <a href="/signup">Create account</a></p>
            <div className="auth-secure-note"><ShieldCheck size={14} /><span>Your workspace is just a sign-in away.</span></div>
            <a className="auth-back" href="/">← Back to home</a>
          </section>
        </div>
      )}
    </main>
  );
}
