import React, { useState, useEffect, CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store";

/* ─────────────────────────────────────────
   IBM Carbon Design System tokens (inline)
   https://carbondesignsystem.com/
───────────────────────────────────────── */
const carbon = {
  /* Core palette */
  gray100: "#161616",
  gray90: "#262626",
  gray80: "#393939",
  gray70: "#525252",
  gray60: "#6f6f6f",
  gray30: "#c6c6c6",
  gray10: "#f4f4f4",
  white: "#ffffff",

  /* Brand / Interactive */
  blue60: "#0f62fe",
  blue50: "#4589ff",
  blue40: "#78a9ff",
  blue30: "#a6c8ff",
  blue20: "#d0e2ff",
  blue10: "#edf5ff",

  /* Semantic */
  red60: "#da1e28",
  red40: "#ff8389",
  green50: "#24a148",
  teal50: "#009d9a",

  /* Cyan accent (for ILA brand) */
  cyan50: "#1192e8",
  cyan40: "#33b1ff",
  cyan30: "#82cfff",
  cyan20: "#bae6ff",

  /* Spacing (4-base) */
  spacing01: "2px",
  spacing02: "4px",
  spacing03: "8px",
  spacing04: "12px",
  spacing05: "16px",
  spacing06: "24px",
  spacing07: "32px",
  spacing08: "40px",
  spacing09: "48px",
  spacing10: "64px",
  spacing11: "80px",
  spacing12: "96px",
  spacing13: "160px",

  /* Type ramp */
  label01: { fontSize: "12px", lineHeight: "16px", letterSpacing: "0.32px" },
  helperText01: { fontSize: "12px", lineHeight: "16px", letterSpacing: "0.32px" },
  bodyShort01: { fontSize: "14px", lineHeight: "18px", letterSpacing: "0.16px" },
  bodyShort02: { fontSize: "16px", lineHeight: "22px", letterSpacing: "0px" },
  productiveHeading01: { fontSize: "14px", lineHeight: "18px", letterSpacing: "0.16px", fontWeight: 600 },
  productiveHeading02: { fontSize: "16px", lineHeight: "22px", letterSpacing: "0px", fontWeight: 600 },
  productiveHeading03: { fontSize: "20px", lineHeight: "28px", letterSpacing: "0px", fontWeight: 400 },
  productiveHeading04: { fontSize: "28px", lineHeight: "36px", letterSpacing: "0px", fontWeight: 400 },
  expressiveHeading04: { fontSize: "28px", lineHeight: "36px", letterSpacing: "0px", fontWeight: 600 },

  /* Elevation */
  shadow02: "0 2px 6px rgba(0,0,0,.2)",
  shadow03: "0 4px 12px rgba(0,0,0,.25)",

  /* Border radius — Carbon uses 0 for most components */
  radius: "0px",
};

/* ─────────────────────────────────────────
   Interfaces
───────────────────────────────────────── */
interface UserData {
  username: string;
  role: string;
}

interface LoginProps {}

interface DemoCredential {
  id: string;
  label: string;
  password: string;
  role: string;
  color: string;
}

const DEMO_CREDENTIALS: DemoCredential[] = [
  { id: "admin",   label: "Administrator", password: "admin2026",   role: "ADMIN",    color: carbon.red40 },
  { id: "analyst", label: "Analyst",       password: "ila2026",     role: "ANALYST",  color: carbon.cyan40 },
  { id: "viewer",  label: "Viewer",        password: "viewer2026",  role: "VIEWER",   color: carbon.green50 },
];

/* ─────────────────────────────────────────
   Carbon Text Input
───────────────────────────────────────── */
interface CarbonTextInputProps {
  id: string;
  labelText: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  onEnter?: () => void;
  invalid?: boolean;
  invalidText?: string;
  helperText?: string;
}

const CarbonTextInput: React.FC<CarbonTextInputProps> = ({
  id, labelText, type = "text", value, onChange,
  placeholder, onEnter, invalid, invalidText, helperText,
}) => {
  const [focused, setFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";

  const borderColor = invalid
    ? carbon.red60
    : focused
    ? carbon.blue60
    : carbon.gray60;

  return (
    <div style={{ marginBottom: carbon.spacing05, width: "100%" }}>
      {/* Label */}
      <label
        htmlFor={id}
        style={{
          display: "block",
          fontFamily: "'IBM Plex Sans', sans-serif",
          ...carbon.label01,
          color: invalid ? carbon.red40 : carbon.gray30,
          marginBottom: carbon.spacing02,
          userSelect: "none",
        }}
      >
        {labelText}
      </label>

      {/* Input wrapper */}
      <div style={{ position: "relative" }}>
        <input
          id={id}
          type={isPassword && !showPassword ? "password" : "text"}
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onEnter?.()}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            display: "block",
            width: "100%",
            height: "48px",
            padding: `0 ${isPassword ? "48px" : "16px"} 0 16px`,
            fontFamily: "'IBM Plex Sans', sans-serif",
            ...carbon.bodyShort01,
            color: carbon.white,
            background: carbon.gray80,
            border: `1px solid ${borderColor}`,
            borderBottom: `2px solid ${borderColor}`,
            borderRadius: carbon.radius,
            outline: "none",
            boxSizing: "border-box",
            transition: "border-color 70ms cubic-bezier(0.2,0,0.38,0.9)",
          }}
        />

        {/* Password toggle */}
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((p) => !p)}
            style={{
              position: "absolute",
              right: 0,
              top: 0,
              height: "48px",
              width: "48px",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: carbon.gray30,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 0,
            }}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              /* Eye-off icon */
              <svg width="16" height="16" viewBox="0 0 32 32" fill="currentColor">
                <path d="M5.24 22.51L6.65 21.09C4.9 19.61 3.44 17.73 2.46 16 3.69 13.66 7.28 7.5 16 7.5a13.39 13.39 0 014.87.9l1.46-1.46A15.27 15.27 0 0016 5.5C6.09 5.5 1.86 13.53 1.69 13.88l-.19.38.19.38C2.59 16.08 3.82 18.01 5.24 22.51z" />
                <path d="M16 10.5a5.5 5.5 0 015.29 4L23 12.77A7.5 7.5 0 0016 8.5a7.4 7.4 0 00-2.52.44L15 10.56A5.46 5.46 0 0116 10.5z" />
                <path d="M28.19 14.5l-.19-.38c-.28-.56-1.64-3.09-4.21-5.2l-1.42 1.42C24.26 12.01 25.6 13.91 26.54 16c-1.23 2.34-4.82 8.5-13.54 8.5a13.39 13.39 0 01-4.87-.9l-1.46 1.46A15.27 15.27 0 0013 26.5h3c9.91 0 14.14-8.03 14.31-8.38l.19-.38-.31-.74z" />
                <path d="M16 21.5a5.5 5.5 0 01-5.29-4L9 19.23A7.5 7.5 0 0016 23.5a7.4 7.4 0 002.52-.44L17 21.44A5.46 5.46 0 0116 21.5z" />
                <path d="M4 2.59L2.59 4l26 26L30 28.59z" />
              </svg>
            ) : (
              /* Eye icon */
              <svg width="16" height="16" viewBox="0 0 32 32" fill="currentColor">
                <path d="M30.94 15.66A16.69 16.69 0 0016 5 16.69 16.69 0 001.06 15.66a1 1 0 000 .68A16.69 16.69 0 0016 27a16.69 16.69 0 0014.94-10.66 1 1 0 000-.68zM16 25c-5.3 0-10.9-3.93-12.93-9C5.1 10.93 10.7 7 16 7s10.9 3.93 12.93 9C26.9 21.07 21.3 25 16 25z" />
                <path d="M16 10a6 6 0 106 6 6 6 0 00-6-6zm0 10a4 4 0 114-4 4 4 0 01-4 4z" />
              </svg>
            )}
          </button>
        )}
      </div>

      {/* Helper / Invalid text */}
      {(invalid && invalidText) ? (
        <div
          style={{
            fontFamily: "'IBM Plex Sans', sans-serif",
            ...carbon.helperText01,
            color: carbon.red40,
            marginTop: carbon.spacing02,
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 32 32" fill={carbon.red40}>
            <path d="M16 2C8.3 2 2 8.3 2 16s6.3 14 14 14 14-6.3 14-14S23.7 2 16 2zm-1.1 6h2.2v11h-2.2V8zM16 25c-.8 0-1.5-.7-1.5-1.5S15.2 22 16 22s1.5.7 1.5 1.5S16.8 25 16 25z" />
          </svg>
          {invalidText}
        </div>
      ) : helperText ? (
        <div
          style={{
            fontFamily: "'IBM Plex Sans', sans-serif",
            ...carbon.helperText01,
            color: carbon.gray60,
            marginTop: carbon.spacing02,
          }}
        >
          {helperText}
        </div>
      ) : null}
    </div>
  );
};

/* ─────────────────────────────────────────
   Carbon Button
───────────────────────────────────────── */
interface CarbonButtonProps {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  kind?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg" | "xl" | "2xl";
  loading?: boolean;
  fullWidth?: boolean;
  style?: CSSProperties;
}

const CarbonButton: React.FC<CarbonButtonProps> = ({
  children, onClick, disabled, kind = "primary", loading, fullWidth, style,
}) => {
  const [hovered, setHovered] = useState(false);
  const [active, setActive] = useState(false);

  const bgMap: Record<string, string> = {
    primary: active ? "#002d9c" : hovered ? "#0050e6" : carbon.blue60,
    secondary: active ? "#393939" : hovered ? "#4c4c4c" : carbon.gray80,
    ghost: active ? "rgba(15,98,254,0.12)" : hovered ? "rgba(15,98,254,0.08)" : "transparent",
    danger: active ? "#750e13" : hovered ? "#ba1b23" : carbon.red60,
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setActive(false); }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "space-between",
        width: fullWidth ? "100%" : "auto",
        minHeight: "48px",
        padding: "12px 64px 12px 16px",
        fontFamily: "'IBM Plex Sans', sans-serif",
        fontSize: "14px",
        fontWeight: 600,
        lineHeight: "18px",
        letterSpacing: "0.16px",
        color: kind === "ghost" ? carbon.blue40 : carbon.white,
        background: bgMap[kind],
        border: kind === "ghost" ? `1px solid transparent` : "none",
        borderRadius: carbon.radius,
        cursor: (disabled || loading) ? "not-allowed" : "pointer",
        opacity: (disabled || loading) ? 0.5 : 1,
        transition: "background 70ms cubic-bezier(0.2,0,0.38,0.9)",
        position: "relative",
        overflow: "hidden",
        ...style,
      }}
    >
      <span>{loading ? "Authenticating..." : children}</span>

      {/* Arrow icon */}
      {!loading && (
        <svg
          width="16"
          height="16"
          viewBox="0 0 32 32"
          fill="currentColor"
          style={{ flexShrink: 0 }}
        >
          <path d="M18 6l-1.41 1.41L24.17 15H4v2h20.17l-7.58 7.59L18 26l10-10z" />
        </svg>
      )}

      {/* Loading spinner */}
      {loading && (
        <svg
          width="16"
          height="16"
          viewBox="0 0 32 32"
          fill="currentColor"
          style={{ flexShrink: 0, animation: "cds-spin 0.7s linear infinite" }}
        >
          <path
            opacity=".25"
            d="M16 2a14 14 0 100 28A14 14 0 0016 2zm0 26A12 12 0 1116 4a12 12 0 010 24z"
          />
          <path d="M28 16h2A14 14 0 0016 2v2a12 12 0 0112 12z" />
        </svg>
      )}
    </button>
  );
};

/* ─────────────────────────────────────────
   Carbon Tag (for demo credentials)
───────────────────────────────────────── */
interface CarbonTagProps {
  label: string;
  sublabel: string;
  color: string;
  onClick: () => void;
}

const CarbonTag: React.FC<CarbonTagProps> = ({ label, sublabel, color, onClick }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        height: "24px",
        padding: "0 8px",
        background: hovered ? `${color}22` : `${color}14`,
        border: `1px solid ${color}55`,
        borderRadius: "0px",
        cursor: "pointer",
        transition: "all 70ms ease",
      }}
    >
      <span
        style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: "11px",
          fontWeight: 600,
          color,
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontSize: "11px",
          color: carbon.gray30,
          letterSpacing: "0.16px",
        }}
      >
        · {sublabel}
      </span>
    </button>
  );
};

/* ─────────────────────────────────────────
   Main Login Component
───────────────────────────────────────── */
const Login: React.FC<LoginProps> = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [time, setTime] = useState<Date>(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const utcTime = time.toUTCString().split(" ")[4];
  const dateStr = time
    .toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    .toUpperCase();

  const handleLogin = (): void => {
    if (!username || !password) {
      setError("Please fill in all required fields.");
      return;
    }
    setLoading(true);
    setError("");

    setTimeout(() => {
      const match = DEMO_CREDENTIALS.find(
        (c) => c.id === username.toLowerCase() && c.password === password
      );
      if (match) {
        const token = `token_${match.id}_${Date.now()}`;
        login({ username: match.id, role: match.role } as any, token);
        navigate("/Sidebar");
      } else {
        setError("Invalid credentials. Please try again.");
        setLoading(false);
      }
    }, 1400);
  };

  const fillDemo = (cred: DemoCredential) => {
    setUsername(cred.id);
    setPassword(cred.password);
    setError("");
  };

  return (
    <div style={s.root}>
      {/* Inject font + keyframes */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
        @keyframes cds-spin { to { transform: rotate(360deg); } }
        @keyframes cds-fade-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        * { box-sizing: border-box; }
        input::placeholder { color: #525252; }
        input:-webkit-autofill,
        input:-webkit-autofill:hover,
        input:-webkit-autofill:focus {
          -webkit-box-shadow: 0 0 0 40px #393939 inset !important;
          -webkit-text-fill-color: #ffffff !important;
        }
      `}</style>

      {/* Background grid */}
      <div style={s.bgGrid} />
      <div style={s.scanlines} />
      <div style={s.glowTL} />
      <div style={s.glowBR} />

      {/* ── Top system bar (Carbon Header style) ── */}
      <header style={s.header}>
        <div style={s.headerLeft}>
          {/* Shield icon */}
          <div style={s.headerIcon}>
            <svg width="20" height="20" viewBox="0 0 32 32" fill={carbon.cyan40}>
              <path d="M16 2L4 7v8c0 8.84 5.09 13.91 12 15 6.91-1.09 12-6.16 12-15V7L16 2zm10 13c0 7.52-4.32 11.89-10 13.06C10.32 26.89 6 22.52 6 15V8.3l10-3.89 10 3.89V15z" />
              <path d="M14 21.41L9.29 16.7l1.41-1.41L14 18.59l7.29-7.3 1.42 1.42L14 21.41z" />
            </svg>
          </div>
          <span style={s.headerProductName}>
            <span style={{ fontWeight: 300, color: carbon.gray30 }}>ILA </span>
            <span style={{ fontWeight: 600 }}>OSINT</span>
          </span>
        </div>

        <div style={s.headerRight}>
          <span style={{ color: carbon.gray60, letterSpacing: "0.32px" }}>
            Intelligence Platform v0.1.0
          </span>
          <span style={s.headerDivider} />
          <span style={{ color: carbon.gray60 }}>
            {utcTime} UTC
          </span>
          <span style={s.headerDivider} />
          <span
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              color: carbon.green50,
              fontSize: "12px",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: carbon.green50,
                display: "inline-block",
              }}
            />
            SYSTEMS NOMINAL
          </span>
        </div>
      </header>

      {/* ── Main stage ── */}
      <main style={s.stage}>
        {/* Left panel — branding */}
        <div style={s.brandPanel}>
          <div style={s.brandContent}>
            <div style={s.logoMark}>
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect
                  x="4" y="4" width="40" height="40"
                  stroke={carbon.cyan40} strokeWidth="1.5"
                  fill="rgba(51,177,255,0.06)"
                />
                <rect
                  x="12" y="12" width="24" height="24"
                  stroke={`${carbon.cyan40}55`} strokeWidth="0.8"
                  fill="none"
                />
                <text
                  x="24" y="28"
                  textAnchor="middle"
                  fontFamily="'IBM Plex Sans', sans-serif"
                  fontSize="11"
                  fontWeight="700"
                  fill={carbon.cyan40}
                  letterSpacing="1"
                >
                  ILA
                </text>
              </svg>
            </div>

            <h1 style={s.brandTitle}>ILA OSINT</h1>
            <p style={s.brandSubtitle}>Intelligence Platform v0.1.0</p>
            <p style={s.brandTagline}>
              Digital Intelligence · Threat & Narrative Monitoring
            </p>

            <div style={s.brandDivider} />

            <div style={s.brandFeatures}>
              {[
                "Real-time threat intelligence",
                "Multi-source OSINT collection",
                "Narrative monitoring & analysis",
                "Automated entity resolution",
              ].map((f) => (
                <div key={f} style={s.brandFeatureItem}>
                  <svg width="16" height="16" viewBox="0 0 32 32" fill={carbon.cyan40}>
                    <path d="M14 21.414l-5-5.001L10.413 15 14 18.586 21.585 11 23 12.415z" />
                    <path d="M16 2a14 14 0 100 28A14 14 0 0016 2zm0 26A12 12 0 1116 4a12 12 0 010 24z" />
                  </svg>
                  <span>{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right panel — login form */}
        <div style={s.formPanel}>
          <div style={s.formCard}>
            {/* Carbon tile top accent */}
            <div style={s.cardTopBar} />

            <div style={s.formHeader}>
              <h2 style={s.formTitle}>Sign in</h2>
              <p style={s.formSubtitle}>
                Use your ILA analyst credentials
              </p>
            </div>

            <div style={{ marginTop: carbon.spacing07 }}>
              <CarbonTextInput
                id="username"
                labelText="USERNAME"
                type="text"
                value={username}
                onChange={setUsername}
                placeholder="analyst"
                helperText=""
              />

              <CarbonTextInput
                id="password"
                labelText="PASSWORD"
                type="password"
                value={password}
                onChange={setPassword}
                placeholder="••••••••"
                onEnter={handleLogin}
                invalid={!!error}
                invalidText={error}
              />
            </div>

            {/* Carbon inline notification */}
            {error && (
              <div style={s.inlineNotification}>
                <svg width="16" height="16" viewBox="0 0 32 32" fill={carbon.red40} style={{ flexShrink: 0 }}>
                  <path d="M16 2C8.3 2 2 8.3 2 16s6.3 14 14 14 14-6.3 14-14S23.7 2 16 2zm-1.1 6h2.2v11h-2.2V8zM16 25c-.8 0-1.5-.7-1.5-1.5S15.2 22 16 22s1.5.7 1.5 1.5S16.8 25 16 25z" />
                </svg>
                <div>
                  <p style={{ ...carbon.productiveHeading01 as CSSProperties, color: carbon.red40, margin: 0 }}>
                    Access Denied
                  </p>
                  <p style={{ ...carbon.bodyShort01 as CSSProperties, color: carbon.gray30, margin: "2px 0 0" }}>
                    {error}
                  </p>
                </div>
              </div>
            )}

            <div style={{ marginTop: carbon.spacing06 }}>
              <CarbonButton
                kind="primary"
                fullWidth
                loading={loading}
                onClick={handleLogin}
              >
                SIGN IN
              </CarbonButton>
            </div>

            {/* Security note */}
            <p style={s.securityNote}>
              <svg width="12" height="12" viewBox="0 0 32 32" fill={carbon.gray60} style={{ flexShrink: 0, marginTop: 1 }}>
                <path d="M16 2L4 7v8c0 8.84 5.09 13.91 12 15 6.91-1.09 12-6.16 12-15V7L16 2zm10 13c0 7.52-4.32 11.89-10 13.06C10.32 26.89 6 22.52 6 15V8.3l10-3.89 10 3.89V15z" />
              </svg>
              AUTHORIZED PERSONNEL ONLY · ALL ACTIVITY IS LOGGED
            </p>

            {/* Demo credentials section (Carbon tile style) */}
            <div style={s.demoSection}>
              <p style={s.demoLabel}>DEMO CREDENTIALS</p>
              <div style={s.demoTags}>
                {DEMO_CREDENTIALS.map((c) => (
                  <CarbonTag
                    key={c.id}
                    label={c.id}
                    sublabel={c.label}
                    color={c.color}
                    onClick={() => fillDemo(c)}
                  />
                ))}
              </div>
            </div>
          </div>

          <p style={s.footerText}>
            POWERED BY PROJECT HORIZON
          </p>
        </div>
      </main>
    </div>
  );
};

export default Login;

/* ─────────────────────────────────────────
   Styles — Carbon spacing, type, and colors
───────────────────────────────────────── */
const s: Record<string, CSSProperties> = {
  root: {
    width: "100vw",
    height: "100vh",
    background: carbon.gray100,
    position: "relative",
    overflow: "hidden",
    fontFamily: "'IBM Plex Sans', sans-serif",
    display: "flex",
    flexDirection: "column",
  },

  bgGrid: {
    position: "fixed",
    inset: 0,
    zIndex: 0,
    pointerEvents: "none",
    backgroundImage: `
      linear-gradient(rgba(51,177,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(51,177,255,0.03) 1px, transparent 1px)
    `,
    backgroundSize: "32px 32px",
  },

  scanlines: {
    position: "fixed",
    inset: 0,
    zIndex: 0,
    pointerEvents: "none",
    background:
      "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 4px)",
  },

  glowTL: {
    position: "fixed",
    top: -120,
    left: -120,
    width: 480,
    height: 480,
    zIndex: 0,
    background: "radial-gradient(circle, rgba(51,177,255,0.07) 0%, transparent 70%)",
    pointerEvents: "none",
  },

  glowBR: {
    position: "fixed",
    bottom: -120,
    right: -120,
    width: 480,
    height: 480,
    zIndex: 0,
    background: "radial-gradient(circle, rgba(15,98,254,0.06) 0%, transparent 70%)",
    pointerEvents: "none",
  },

  /* Carbon Header */
  header: {
    position: "relative",
    zIndex: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    height: "48px",
    padding: "0 16px",
    background: carbon.gray90,
    borderBottom: `1px solid ${carbon.gray80}`,
    flexShrink: 0,
  },

  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },

  headerIcon: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "32px",
    height: "48px",
    borderRight: `1px solid ${carbon.gray80}`,
    paddingRight: "12px",
    marginRight: "4px",
  },

  headerProductName: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: "14px",
    lineHeight: "18px",
    letterSpacing: "0.16px",
    color: carbon.white,
  },

  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "11px",
    letterSpacing: "0.32px",
  },

  headerDivider: {
    width: "1px",
    height: "16px",
    background: carbon.gray80,
    display: "inline-block",
  },

  /* Stage layout */
  stage: {
    position: "relative",
    zIndex: 5,
    flex: 1,
    display: "flex",
    alignItems: "stretch",
    overflow: "hidden",
  },

  /* Brand panel */
  brandPanel: {
    flex: "1 1 0",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "48px",
    borderRight: `1px solid ${carbon.gray80}`,
  },

  brandContent: {
    maxWidth: "360px",
    animation: "cds-fade-in 0.4s ease both",
  },

  logoMark: {
    marginBottom: "24px",
  },

  brandTitle: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: "42px",
    lineHeight: "50px",
    fontWeight: 700,
    letterSpacing: "-0.01em",
    color: carbon.white,
    margin: "0 0 8px",
  },

  brandSubtitle: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "13px",
    color: carbon.cyan40,
    letterSpacing: "0.08em",
    margin: "0 0 6px",
  },

  brandTagline: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: "13px",
    color: carbon.gray60,
    letterSpacing: "0.16px",
    margin: 0,
  },

  brandDivider: {
    height: "1px",
    background: carbon.gray80,
    margin: "32px 0",
  },

  brandFeatures: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },

  brandFeatureItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: "13px",
    color: carbon.gray30,
    letterSpacing: "0.16px",
    lineHeight: "20px",
  },

  /* Form panel */
  formPanel: {
    width: "480px",
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "48px 40px",
    overflowY: "auto",
  },

  formCard: {
    width: "100%",
    background: carbon.gray90,
    border: `1px solid ${carbon.gray80}`,
    padding: "0 0 32px",
    animation: "cds-fade-in 0.45s ease 0.1s both",
    position: "relative",
  },

  cardTopBar: {
    height: "4px",
    background: carbon.blue60,
    width: "100%",
    marginBottom: "32px",
  },

  formHeader: {
    padding: "0 32px",
  },

  formTitle: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: "28px",
    lineHeight: "36px",
    fontWeight: 400,
    color: carbon.white,
    margin: "0 0 8px",
    letterSpacing: "0px",
  },

  formSubtitle: {
    fontFamily: "'IBM Plex Sans', sans-serif",
    fontSize: "14px",
    lineHeight: "20px",
    color: carbon.gray60,
    margin: 0,
    letterSpacing: "0.16px",
  },

  formFields: {
    padding: "0 32px",
    marginTop: "32px",
  },

  inlineNotification: {
    display: "flex",
    alignItems: "flex-start",
    gap: "12px",
    padding: "12px 16px",
    background: "rgba(218,30,40,0.1)",
    borderLeft: `3px solid ${carbon.red60}`,
    margin: "0 32px",
    marginTop: "16px",
  },

  securityNote: {
    display: "flex",
    alignItems: "flex-start",
    gap: "6px",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "10px",
    letterSpacing: "0.32px",
    color: carbon.gray60,
    textAlign: "center",
    justifyContent: "center",
    margin: "16px 32px 0",
    lineHeight: "16px",
  },

  demoSection: {
    margin: "24px 32px 0",
    padding: "16px",
    background: carbon.gray80,
    border: `1px solid ${carbon.gray70}`,
  },

  demoLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "10px",
    letterSpacing: "0.32px",
    color: carbon.gray60,
    margin: "0 0 10px",
  },

  demoTags: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: "8px",
  },

  footerText: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "11px",
    letterSpacing: "0.32px",
    color: carbon.gray70,
    marginTop: "24px",
    textAlign: "center" as const,
  },
};