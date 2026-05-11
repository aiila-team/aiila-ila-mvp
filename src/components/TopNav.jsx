import { useState, useEffect } from 'react';

export default function TopNav({ title, subtitle }) {
  const [time, setTime] = useState(new Date());
  const [searchVal, setSearchVal] = useState('');

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <header style={{
      height: '56px',
      background: '#0D0F14',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 24px',
      gap: '16px',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Page title */}
      <div>
        <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '14px', color: '#F1F5F9' }}>{title}</div>
        {subtitle && <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>{subtitle}</div>}
      </div>

      {/* Divider */}
      <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)' }} />

      {/* Search */}
      <div style={{ flex: 1, maxWidth: '400px', position: 'relative' }}>
        <span style={{
          position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)',
          fontSize: '12px', color: '#4B5563',
        }}>⌕</span>
        <input
          value={searchVal}
          onChange={e => setSearchVal(e.target.value)}
          placeholder="Search entities, alerts, IDs..."
          style={{
            width: '100%',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px',
            padding: '6px 12px 6px 28px',
            fontSize: '12px',
            color: '#D1D5DB',
            fontFamily: 'Inter, sans-serif',
            outline: 'none',
            transition: 'border 0.2s',
          }}
          onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.4)'}
          onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
        />
        {searchVal && (
          <span style={{
            position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
            fontSize: '10px', color: '#4B5563', cursor: 'pointer',
          }} onClick={() => setSearchVal('')}>✕</span>
        )}
      </div>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Threat level */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>THREAT LEVEL</span>
          <div style={{
            padding: '2px 8px',
            background: 'rgba(239,68,68,0.12)',
            border: '1px solid rgba(239,68,68,0.25)',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: '600',
            color: '#EF4444',
            fontFamily: 'JetBrains Mono, monospace',
            letterSpacing: '0.05em',
          }}>HIGH</div>
        </div>

        {/* Time */}
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563' }}>
          {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          <span style={{ marginLeft: '4px', color: '#374151' }}>IST</span>
        </div>

        {/* Alert bell */}
        <div style={{ position: 'relative', cursor: 'pointer' }}>
          <span style={{ fontSize: '16px', color: '#6B7280' }}>🔔</span>
          <span style={{
            position: 'absolute', top: '-4px', right: '-5px',
            width: '14px', height: '14px',
            background: '#EF4444',
            borderRadius: '50%',
            fontSize: '8px',
            color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'JetBrains Mono, monospace',
            fontWeight: '700',
          }}>5</span>
        </div>
      </div>
    </header>
  );
}
