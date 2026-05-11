import { useState, useEffect } from 'react';
import TopNav from '../components/TopNav.jsx';
import { MOCK_SOURCES } from '../mockData.js';
import { formatRelativeTime, getSourceTierLabel } from '../utils.js';

const SOURCE_TYPE_ICONS = {
  telegram: '📡',
  rss: '📰',
  social: '🐦',
  mock: '⚙',
};

export default function SourceMonitor() {
  const [sources, setSources] = useState(MOCK_SOURCES);
  const [tick, setTick] = useState(0);

  // Simulate live event count updates
  useEffect(() => {
    const t = setInterval(() => {
      setTick(p => p + 1);
      setSources(prev => prev.map(s => ({
        ...s,
        events_today: s.events_today + Math.floor(Math.random() * 3),
        last_crawl: s.status === 'active' ? new Date(Date.now() - Math.random() * 8 * 60000).toISOString() : s.last_crawl,
      })));
    }, 7000);
    return () => clearInterval(t);
  }, []);

  const totalEvents = sources.reduce((acc, s) => acc + s.events_today, 0);
  const activeSources = sources.filter(s => s.status === 'active').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopNav
        title="Source Monitor"
        subtitle={`${activeSources} ACTIVE · ${totalEvents} EVENTS TODAY`}
      />

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
        {/* Stats row */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
          {[
            { label: 'ACTIVE SOURCES', value: activeSources, color: '#34D399' },
            { label: 'EVENTS TODAY', value: totalEvents.toLocaleString(), color: '#60A5FA' },
            { label: 'LAST CRAWL', value: '< 8m', color: '#F59E0B' },
            { label: 'INGESTION RATE', value: `~${Math.round(totalEvents / 24)}/hr`, color: '#A78BFA' },
          ].map(stat => (
            <div key={stat.label} style={{
              flex: 1,
              background: '#13161D',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '10px',
              padding: '14px 16px',
            }}>
              <div style={{ fontSize: '9px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px', letterSpacing: '0.06em' }}>
                {stat.label}
              </div>
              <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '700', fontSize: '22px', color: stat.color }}>
                {stat.value}
              </div>
            </div>
          ))}
        </div>

        {/* Source table */}
        <div style={{
          background: '#13161D',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '10px',
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
            padding: '10px 16px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            background: '#0D0F14',
          }}>
            {['SOURCE', 'STATUS', 'TIER', 'EVENTS TODAY', 'LAST CRAWL'].map(h => (
              <div key={h} style={{
                fontSize: '9px',
                color: '#374151',
                fontFamily: 'JetBrains Mono, monospace',
                letterSpacing: '0.06em',
              }}>{h}</div>
            ))}
          </div>

          {/* Rows */}
          {sources.map((source, i) => (
            <div key={source.id} style={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
              padding: '14px 16px',
              alignItems: 'center',
              borderBottom: i < sources.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              {/* Name */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '16px' }}>{SOURCE_TYPE_ICONS[source.type] || '◎'}</span>
                <div>
                  <div style={{ fontSize: '13px', color: '#D1D5DB', fontWeight: '500', fontFamily: 'Inter, sans-serif' }}>
                    {source.name}
                  </div>
                  <div style={{ fontSize: '10px', color: '#374151', fontFamily: 'JetBrains Mono, monospace' }}>
                    {source.type.toUpperCase()}
                  </div>
                </div>
              </div>

              {/* Status */}
              <div>
                <span style={{
                  fontSize: '10px',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontWeight: '600',
                  color: source.status === 'active' ? '#34D399' : '#EF4444',
                  background: source.status === 'active' ? 'rgba(52,211,153,0.1)' : 'rgba(239,68,68,0.1)',
                  padding: '3px 8px',
                  borderRadius: '4px',
                }}>
                  {source.status === 'active' ? '● ACTIVE' : '✕ ERROR'}
                </span>
              </div>

              {/* Tier */}
              <div style={{ fontSize: '11px', color: '#6B7280', fontFamily: 'JetBrains Mono, monospace' }}>
                {getSourceTierLabel(source.tier).split(' — ')[0]}
              </div>

              {/* Events */}
              <div style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '13px',
                color: '#F1F5F9',
                fontWeight: '500',
              }}>
                {source.events_today.toLocaleString()}
              </div>

              {/* Last crawl */}
              <div style={{ fontSize: '11px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>
                {formatRelativeTime(source.last_crawl)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
