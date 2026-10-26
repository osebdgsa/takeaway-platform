import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../api";
import { useAuth } from "../auth";
import { DEMO_CREDENTIALS } from "../credentials";

export default function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
      navigate("/restaurants");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-grid">
      <section className="card">
        <h1>{mode === "login" ? "Sign in" : "Create account"}</h1>
        <p className="muted">
          Sign-up always creates a <strong>customer</strong>; admin accounts are
          created by the seed script.
        </p>

        <div className="tabs">
          <button
            type="button"
            className={mode === "login" ? "tab active" : "tab"}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "register" ? "tab active" : "tab"}
            onClick={() => {
              setMode("register");
              setError(null);
            }}
          >
            Register
          </button>
        </div>

        <form onSubmit={onSubmit} className="stack">
          {mode === "register" && (
            <label>
              Full name
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                minLength={1}
                placeholder="Jane Doe"
              />
            </label>
          )}
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              placeholder="you@example.com"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              placeholder="at least 8 characters"
            />
          </label>

          {error && <p className="alert alert-error">{error}</p>}

          <button className="btn btn-primary" disabled={busy} type="submit">
            {busy ? "Working…" : mode === "login" ? "Sign in" : "Register"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Demo accounts</h2>
        <p className="muted">
          Click <em>Use</em> to fill the form, then sign in.
        </p>
        <ul className="credential-list">
          {DEMO_CREDENTIALS.map((credential) => (
            <li key={credential.email} className="credential">
              <div className="credential-head">
                <strong>{credential.label}</strong>
                <span className={`badge badge-${credential.role}`}>
                  {credential.role}
                </span>
              </div>
              <code className="credential-line">
                {credential.email} / {credential.password}
              </code>
              <p className="muted small">{credential.expected}</p>
              <button
                type="button"
                className="btn btn-small"
                onClick={() => {
                  setMode("login");
                  setEmail(credential.email);
                  setPassword(credential.password);
                  setError(null);
                }}
              >
                Use
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
