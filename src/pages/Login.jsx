import { useState, useEffect } from 'react';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const utcTime = time.toUTCString().split(' ')[4];
  const dateStr = time.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase();

  const handleLogin = () => {
    if (!username || !password) { setError('CREDENTIALS REQUIRED'); return; }
    setLoading(true);
    setError('');
    setTimeout(() => {
      if (username === 'analyst' && password === 'ila2026') {
        onLogin({ username, role: 'ANALYST' });
      } else {
        setError('ACCESS DENIED — INVALID CREDENTIALS');
        setLoading(false);
      }
    }, 1400);
  };

  return (
    <div style={css.root}>
      <div style={css.bgGrid} />
      <div style={css.scanlines} />
      <div style={css.glowTL} />
      <div style={css.glowBR} />

      {/* Top status bar */}
      <div style={css.statusBar}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={css.liveDot} />
          SYS STATUS: NOMINAL
        </span>
        <span style={{ color: 'rgba(0,194,255,0.32)', letterSpacing: '0.12em' }}>
          ILA SOVEREIGN INTELLIGENCE PLATFORM · v1.0
        </span>
        <span>{utcTime} UTC · {dateStr}</span>
      </div>

      {/* Center stage */}
      <div style={css.stage}>
        <div style={css.classBanner}>
          ◼ CLASSIFIED · AUTHORIZED ACCESS ONLY ◼
        </div>

        <div style={css.card}>
          {/* Top gradient line */}
          <div style={css.topLine} />

          {/* Logo */}
          <div style={css.logoWrap}>
            <div style={css.logoBox}>
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <polygon
                  points="16,2 28,9 28,23 16,30 4,23 4,9"
                  stroke="#00C2FF" strokeWidth="1.2" fill="rgba(0,194,255,0.07)"
                />
                <polygon
                  points="16,7 23,11.5 23,20.5 16,25 9,20.5 9,11.5"
                  stroke="rgba(0,229,255,0.35)" strokeWidth="0.7" fill="none"
                />
                <text x="16" y="19.5" textAnchor="middle"
                  fontFamily="Space Grotesk, sans-serif"
                  fontSize="7.5" fontWeight="700" fill="#00C2FF">
                  ILA
                </text>
              </svg>
            </div>
            <div style={css.logoName}>ILA</div>
            <div style={css.logoSub}>
              INTELLIGENCE LAYER FOR ANALYTICS<br />
              OSINT OPERATIONS PLATFORM
            </div>
          </div>

          <div style={css.divider} />

          {/* Username field */}
          <InputField
            label="ANALYST IDENTIFIER"
            type="text"
            value={username}
            onChange={setUsername}
            placeholder="analyst"
          />

          {/* Password field */}
          <InputField
            label="ACCESS CODE"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••••"
            onEnter={handleLogin}
          />

          {/* Error message */}
          {error && (
            <div style={css.errorBox}>
              ⚠ {error}
            </div>
          )}

          {/* Submit button */}
          <LoginButton loading={loading} onClick={handleLogin} />

          <div style={css.demoHint}>
            Demo access: <span style={{ color: 'rgba(0,194,255,0.5)' }}>analyst</span>
            {' '}/ <span style={{ color: 'rgba(0,194,255,0.5)' }}>ila2026</span>
          </div>
        </div>

        <div style={css.footerText}>
          AIILA TEAM &nbsp;&middot;&nbsp; RESTRICTED USE ONLY &nbsp;&middot;&nbsp; {dateStr}
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ── */

function InputField({ label, type, value, onChange, placeholder, onEnter }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9, letterSpacing: '0.14em', color: '#4A5E72', marginBottom: 7,
      }}>
        <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#00C2FF', display: 'inline-block', flexShrink: 0 }} />
        {label}
      </div>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck="false"
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && onEnter?.()}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: '100%',
          background: 'rgba(7,17,31,0.9)',
          border: `1px solid ${focused ? 'rgba(0,194,255,0.45)' : 'rgba(0,180,255,0.1)'}`,
          boxShadow: focused ? '0 0 0 2px rgba(0,194,255,0.07)' : 'none',
          borderRadius: 7,
          padding: '10px 14px',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 13, color: '#E6F1FF',
          outline: 'none',
          transition: 'border-color 0.2s, box-shadow 0.2s',
          letterSpacing: '0.04em',
        }}
      />
    </div>
  );
}

function LoginButton({ loading, onClick }) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={loading}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: '100%', padding: '12px',
        background: hovered && !loading ? 'rgba(0,194,255,0.18)' : 'rgba(0,194,255,0.1)',
        border: '1px solid rgba(0,194,255,0.4)',
        borderRadius: 7, color: '#00E5FF',
        fontFamily: 'Syne, sans-serif',
        fontSize: 12, fontWeight: 600,
        letterSpacing: '0.14em',
        cursor: loading ? 'not-allowed' : 'pointer',
        opacity: loading ? 0.65 : 1,
        boxShadow: hovered && !loading ? '0 0 14px rgba(0,194,255,0.18)' : 'none',
        transition: 'all 0.2s',
      }}
    >
      {loading ? 'AUTHENTICATING...' : 'AUTHENTICATE & ACCESS PLATFORM'}
    </button>
  );
}

/* ── Styles ── */
const css = {
  root: {
    width: '100vw', height: '100vh',
    background: '#050816',
    position: 'relative', overflow: 'hidden',
    fontFamily: 'Inter, sans-serif',
  },
  bgGrid: {
    position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
    backgroundImage: `
      linear-gradient(rgba(0,194,255,0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,194,255,0.025) 1px, transparent 1px)
    `,
    backgroundSize: '48px 48px',
  },
  scanlines: {
    position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
    background: 'repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.06) 2px,rgba(0,0,0,0.06) 4px)',
  },
  glowTL: {
    position: 'fixed', top: -80, left: -80, width: 360, height: 360, zIndex: 0,
    background: 'radial-gradient(circle, rgba(0,194,255,0.09) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  glowBR: {
    position: 'fixed', bottom: -100, right: -100, width: 420, height: 420, zIndex: 0,
    background: 'radial-gradient(circle, rgba(0,100,200,0.08) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  statusBar: {
    position: 'fixed', top: 0, left: 0, right: 0,
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '9px 24px',
    borderBottom: '1px solid rgba(0,180,255,0.07)',
    background: 'rgba(5,8,22,0.85)',
    backdropFilter: 'blur(8px)',
    zIndex: 10,
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 9.5, color: '#4A5E72', letterSpacing: '0.1em',
  },
  liveDot: {
    display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
    background: '#00E676', boxShadow: '0 0 6px #00E676',
    flexShrink: 0,
  },
  stage: {
    position: 'relative', zIndex: 2,
    width: '100%', height: '100%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexDirection: 'column',
  },
  classBanner: {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 9.5, letterSpacing: '0.18em',
    color: 'rgba(255,176,32,0.55)',
    marginBottom: 18, textAlign: 'center',
  },
  card: {
    width: 400,
    background: 'rgba(13,27,42,0.94)',
    border: '1px solid rgba(0,194,255,0.18)',
    borderRadius: 12,
    padding: '32px',
    boxShadow: '0 0 20px rgba(0,194,255,0.1), 0 32px 64px rgba(0,0,0,0.55)',
    backdropFilter: 'blur(12px)',
  },
  topLine: {
    height: 1.5,
    background: 'linear-gradient(90deg, transparent, #00C2FF, transparent)',
    marginBottom: 26, opacity: 0.65,
  },
  logoWrap: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    marginBottom: 24, gap: 7,
  },
  logoBox: {
    width: 56, height: 56,
    border: '1.5px solid rgba(0,194,255,0.22)',
    borderRadius: 12,
    background: 'rgba(0,194,255,0.06)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 0 22px rgba(0,194,255,0.13)',
    marginBottom: 4,
  },
  logoName: {
    fontFamily: 'Syne, sans-serif',
    fontSize: 22, fontWeight: 700,
    letterSpacing: '0.14em', color: '#E6F1FF',
  },
  logoSub: {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 8.5, letterSpacing: '0.14em',
    color: '#3A4E62', textAlign: 'center', lineHeight: 1.8,
  },
  divider: {
    height: 1,
    background: 'linear-gradient(90deg, transparent, rgba(0,194,255,0.18), transparent)',
    marginBottom: 22,
  },
  errorBox: {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 10, color: '#FF5252',
    letterSpacing: '0.06em',
    marginBottom: 12, textAlign: 'center',
    padding: '7px 12px',
    border: '1px solid rgba(255,82,82,0.25)',
    borderRadius: 5,
    background: 'rgba(255,82,82,0.05)',
  },
  demoHint: {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 9, letterSpacing: '0.08em',
    color: '#3A4E62', textAlign: 'center', marginTop: 14,
  },
  footerText: {
    marginTop: 22,
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 9, letterSpacing: '0.1em',
    color: 'rgba(74,94,114,0.32)',
  },
};