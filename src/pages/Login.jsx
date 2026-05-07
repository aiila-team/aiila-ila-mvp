import { useState } from 'react';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = () => {
    if (!username || !password) { setError('Credentials required'); return; }
    setLoading(true);
    setTimeout(() => {
      if (username === 'analyst' && password === 'ila2026') {
        onLogin({ username, role: 'ANALYST' });
      } else {
        setError('Invalid credentials');
        setLoading(false);
      }
    }, 1000);
  };

  return (
    <div style={{
      width: '100vw', height: '100vh',
      background: '#07080A',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background grid */}
      <div style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: `
          linear-gradient(rgba(245,158,11,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(245,158,11,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
      }} />

      {/* Corner decorations */}
      <div style={{ position: 'absolute', top: '20px', left: '20px', fontSize: '10px', color: '#1A1E27', fontFamily: 'JetBrains Mono, monospace' }}>
        ◈ ILA SOVEREIGN INTELLIGENCE PLATFORM v0.1
      </div>
      <div style={{ position: 'absolute', top: '20px', right: '20px', fontSize: '10px', color: '#1A1E27', fontFamily: 'JetBrains Mono, monospace' }}>
        CLASSIFIED — RESTRICTED ACCESS
      </div>

      {/* Login card */}
      <div style={{
        width: '360px',
        background: '#0D0F14',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '14px',
        padding: '36px 32px',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            width: '48px', height: '48px',
            background: 'linear-gradient(135deg, #F59E0B, #D97706)',
            borderRadius: '12px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 12px',
            fontSize: '22px', fontWeight: '700', color: '#000',
            fontFamily: 'Syne, sans-serif',
          }}>I</div>
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '700', fontSize: '20px', color: '#F1F5F9', letterSpacing: '0.05em' }}>
            ILA OSINT
          </div>
          <div style={{ fontSize: '10px', color: '#374151', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.1em', marginTop: '4px' }}>
            INTELLIGENCE LAYER FOR ANALYTICS
          </div>
        </div>

        {/* Hint */}
        <div style={{
          background: 'rgba(245,158,11,0.06)',
          border: '1px solid rgba(245,158,11,0.15)',
          borderRadius: '6px',
          padding: '8px 12px',
          marginBottom: '20px',
          fontSize: '11px',
          color: '#F59E0B',
          fontFamily: 'JetBrains Mono, monospace',
          textAlign: 'center',
        }}>
          Demo: analyst / ila2026
        </div>

        {/* Fields */}
        {[
          { label: 'ANALYST ID', value: username, set: setUsername, type: 'text', placeholder: 'analyst' },
          { label: 'ACCESS CODE', value: password, set: setPassword, type: 'password', placeholder: '••••••••' },
        ].map(f => (
          <div key={f.label} style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em', marginBottom: '6px' }}>
              {f.label}
            </div>
            <input
              type={f.type}
              value={f.value}
              onChange={e => f.set(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
              placeholder={f.placeholder}
              style={{
                width: '100%',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '7px',
                padding: '10px 14px',
                fontSize: '13px',
                color: '#D1D5DB',
                fontFamily: 'Inter, sans-serif',
                outline: 'none',
                boxSizing: 'border-box',
              }}
              onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.4)'}
              onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
            />
          </div>
        ))}

        {error && (
          <div style={{
            fontSize: '11px',
            color: '#EF4444',
            fontFamily: 'JetBrains Mono, monospace',
            marginBottom: '12px',
            textAlign: 'center',
          }}>⚠ {error}</div>
        )}

        <button
          onClick={handleLogin}
          disabled={loading}
          style={{
            width: '100%',
            padding: '11px',
            background: loading ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.15)',
            border: '1px solid rgba(245,158,11,0.4)',
            borderRadius: '7px',
            color: '#F59E0B',
            fontSize: '13px',
            fontFamily: 'Syne, sans-serif',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            letterSpacing: '0.05em',
            transition: 'all 0.2s',
          }}
          onMouseEnter={e => { if (!loading) e.currentTarget.style.background = 'rgba(245,158,11,0.22)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = loading ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.15)'; }}
        >
          {loading ? 'AUTHENTICATING...' : 'ACCESS PLATFORM →'}
        </button>

        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '10px', color: '#1F2937', fontFamily: 'JetBrains Mono, monospace' }}>
          AUTHORIZED ACCESS ONLY · AIILA TEAM
        </div>
      </div>
    </div>
  );
}
