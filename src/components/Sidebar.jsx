import { useState } from 'react';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '⬡', badge: null },
  { id: 'alerts', label: 'Alert Inbox', icon: '⚠', badge: 43 },
  { id: 'entities', label: 'Entities', icon: '◈', badge: null },
  { id: 'graph', label: 'Graph View', icon: '⬡', badge: null },
  { id: 'keywords', label: 'Keywords', icon: '◉', badge: null },
  { id: 'sources', label: 'Sources', icon: '⬚', badge: null },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside style={{
      width: '220px',
      minWidth: '220px',
      background: '#0D0F14',
      borderRight: '1px solid rgba(255,255,255,0.06)',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      position: 'sticky',
      top: 0,
    }}>
      {/* Logo */}
      <div style={{
        padding: '24px 20px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
          <div style={{
            width: '28px', height: '28px',
            background: 'linear-gradient(135deg, #F59E0B, #D97706)',
            borderRadius: '6px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '13px', fontWeight: '700', color: '#000',
            fontFamily: 'Syne, sans-serif',
          }}>I</div>
          <div>
            <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '700', fontSize: '15px', letterSpacing: '0.05em', color: '#F1F5F9' }}>ILA OSINT</div>
          </div>
        </div>
        <div style={{ fontSize: '10px', color: '#4B5563', letterSpacing: '0.1em', fontFamily: 'JetBrains Mono, monospace', paddingLeft: '38px' }}>
          INTELLIGENCE LAYER
        </div>
      </div>

      {/* Live status */}
      <div style={{ padding: '12px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', fontFamily: 'JetBrains Mono, monospace' }}>
          <div className="live-dot" />
          <span style={{ color: '#6B7280' }}>SYSTEM LIVE</span>
          <span style={{ color: '#EF4444', marginLeft: 'auto' }}>v0.1</span>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: '12px 10px', flex: 1 }}>
        {NAV_ITEMS.map(item => {
          const active = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '9px 12px',
                marginBottom: '2px',
                borderRadius: '8px',
                border: 'none',
                background: active ? 'rgba(245,158,11,0.12)' : 'transparent',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s',
                color: active ? '#F59E0B' : '#6B7280',
                borderLeft: active ? '2px solid #F59E0B' : '2px solid transparent',
              }}
              onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#9CA3AF'; } }}
              onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#6B7280'; } }}
            >
              <span style={{ fontSize: '14px', opacity: active ? 1 : 0.6 }}>{item.icon}</span>
              <span style={{ fontSize: '13px', fontFamily: 'Inter, sans-serif', fontWeight: active ? '500' : '400', flex: 1 }}>{item.label}</span>
              {item.badge && (
                <span style={{
                  fontSize: '10px',
                  fontFamily: 'JetBrains Mono, monospace',
                  background: active ? 'rgba(239,68,68,0.2)' : 'rgba(239,68,68,0.15)',
                  color: '#EF4444',
                  borderRadius: '4px',
                  padding: '2px 5px',
                  fontWeight: '600',
                }}>{item.badge}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Analyst info */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <div style={{
          width: '30px', height: '30px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #1D4ED8, #7C3AED)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '11px', fontWeight: '600', color: '#fff',
          fontFamily: 'Syne, sans-serif',
        }}>G</div>
        <div>
          <div style={{ fontSize: '12px', color: '#D1D5DB', fontWeight: '500' }}>Geetanjali</div>
          <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>ANALYST</div>
        </div>
        <button
          style={{
            marginLeft: 'auto',
            background: 'transparent',
            border: 'none',
            color: '#4B5563',
            cursor: 'pointer',
            fontSize: '14px',
            padding: '4px',
          }}
          title="Logout"
        >⟵</button>
      </div>
    </aside>
  );
}
