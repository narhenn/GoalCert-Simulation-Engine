import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Logo, Wordmark } from "../components/Logo";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await login(email.trim(), password);
      nav("/", { replace: true });
    } catch {
      setErr("Invalid email or password. Try the demo credentials below.");
    } finally {
      setBusy(false);
    }
  };

  const fillDemo = () => { setEmail("admin@goalcert.io"); setPassword("GoalCert@2026"); };

  return (
    <div className="login-wrap">
      {/* form side */}
      <div className="login-form-side">
        <form className="login-card" onSubmit={submit}>
          <div className="brand"><Wordmark size={26} /></div>
          <h1>Sign In</h1>
          <div className="sub">Sign in to your cyber-range to stay connected.</div>

          <label>Email</label>
          <input className="form-input" type="email" autoFocus value={email}
            onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />

          <label>Password</label>
          <input className="form-input" type="password" value={password}
            onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 14, fontSize: 12.5 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 7, margin: 0, color: "var(--gc-text2)", cursor: "pointer", textTransform: "none", fontWeight: 500 }}>
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember me
            </label>
            <span style={{ color: "var(--gc-primary)", cursor: "pointer", fontWeight: 500 }}>Forgot password?</span>
          </div>

          {err && <div className="login-err"><i className="fa fa-circle-exclamation" /> {err}</div>}

          <button className="btn btn-primary" type="submit" disabled={busy}
            style={{ width: "100%", marginTop: 20, justifyContent: "center", padding: "12px" }}>
            {busy ? <><span className="spinner" style={{ borderTopColor: "#fff" }} /> Signing in…</> : <>Sign In</>}
          </button>

          <div className="demo" onClick={fillDemo} style={{ cursor: "pointer" }}>
            <b>Demo account</b> — click to fill<br />
            admin@goalcert.io · GoalCert@2026
          </div>
        </form>
      </div>

      {/* brand hero side */}
      <div className="login-hero">
        <svg className="rings" viewBox="0 0 600 600" preserveAspectRatio="xMidYMid slice" aria-hidden>
          {[260, 210, 160, 110].map((r, i) => (
            <circle key={r} cx="300" cy="300" r={r} fill="none" stroke="#fff" strokeWidth="1.5" opacity={0.06 + i * 0.03} />
          ))}
        </svg>
        <div className="mark"><Logo size={230} color="#fff" /></div>
        <div className="name">GoalCert</div>
      </div>
    </div>
  );
}
