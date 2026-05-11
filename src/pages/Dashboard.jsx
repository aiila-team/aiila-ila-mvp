import { useState, useEffect, useRef } from 'react';
import TopNav from '../components/TopNav.jsx';
import { RiskScoreBadge } from '../components/RiskScore.jsx';
import { DASHBOARD_STATS, MOCK_ALERTS } from '../mockData.js';
import { formatRelativeTime } from '../utils.js';

function KPICard({ label, value, unit, trend, color = '#F59E0B', icon }) {
  return (
    <div style={{
      background: '#13161D',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '10px',
      padding: '16px 18px',
      flex: 1,
      minWidth: '140px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>{label}</div>
        <span style={{ fontSize: '16px', opacity: 0.5 }}>{icon}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span style={{
          fontFamily: 'Syne, sans-serif',
          fontWeight: '700',
          fontSize: '28px',
          color,
          lineHeight: 1,
        }}>{value}</span>
        {unit && <span style={{ fontSize: '12px', color: '#4B5563', fontFamily: 'Inter, sans-serif' }}>{unit}</span>}
      </div>
      {trend && (
        <div style={{ fontSize: '11px', color: trend > 0 ? '#EF4444' : '#22C55E', marginTop: '6px', fontFamily: 'JetBrains Mono, monospace' }}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from yesterday
        </div>
      )}
    </div>
  );
}

function MiniChart({ data }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const max = Math.max(...data);
    const step = w / (data.length - 1);
    ctx.clearRect(0, 0, w, h);

    // Area fill
    ctx.beginPath();
    ctx.moveTo(0, h);
    data.forEach((v, i) => {
      ctx.lineTo(i * step, h - (v / max) * (h - 10));
    });
    ctx.lineTo(w, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(245,158,11,0.3)');
    grad.addColorStop(1, 'rgba(245,158,11,0.02)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = i * step;
      const y = h - (v / max) * (h - 10);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#F59E0B';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Last point dot
    const lastX = (data.length - 1) * step;
    const lastY = h - (data[data.length - 1] / max) * (h - 10);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#F59E0B';
    ctx.fill();
  }, [data]);

  return <canvas ref={canvasRef} width={500} height={80} style={{ width: '100%', height: '80px' }} />;
}

export default function DashboardHome({ onNavigate }) {
  const [liveAlerts] = useState(MOCK_ALERTS.slice(0, 3));
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick(p => p + 1), 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopNav title="Dashboard" subtitle="AIILA — ILA v0.1 MVP · MAY 2026" />

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>

        {/* KPI Row */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <KPICard label="ENTITIES TRACKED" value={DASHBOARD_STATS.total_entities} icon="◈" color="#60A5FA" trend={+12} />
          <KPICard label="ALERTS TODAY" value={DASHBOARD_STATS.alerts_today} icon="⚠" color="#F59E0B" trend={+34} />
          <KPICard label="HIGH RISK ENTITIES" value={DASHBOARD_STATS.high_risk_entities} icon="⛨" color="#EF4444" trend={+6} />
          <KPICard label="SOURCES ACTIVE" value={DASHBOARD_STATS.sources_active} unit="/ 5" icon="⬚" color="#34D399" />
        </div>

        {/* Charts + Top Entities */}
        <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
          {/* Alert volume chart */}
          <div style={{
            flex: 2,
            background: '#13161D',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '10px',
            padding: '16px 18px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div>
                <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '13px', color: '#F1F5F9' }}>Alert Volume</div>
                <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>LAST 24 HOURS</div>
              </div>
              <div className="live-dot" style={{ fontSize: '10px', color: '#6B7280', fontFamily: 'JetBrains Mono, monospace' }}>
                LIVE
              </div>
            </div>
            <MiniChart data={DASHBOARD_STATS.alerts_per_hour} />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px' }}>
              {['00:00', '06:00', '12:00', '18:00', '24:00'].map(t => (
                <span key={t} style={{ fontSize: '9px', color: '#2E3340', fontFamily: 'JetBrains Mono, monospace' }}>{t}</span>
              ))}
            </div>
          </div>

          {/* Top risk entities */}
          <div style={{
            flex: 1,
            background: '#13161D',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '10px',
            padding: '16px 18px',
          }}>
            <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '13px', color: '#F1F5F9', marginBottom: '4px' }}>
              Top Risk Entities
            </div>
            <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: '12px' }}>
              HIGHEST SCORED
            </div>
            {MOCK_ALERTS.sort((a, b) => b.risk_score - a.risk_score).slice(0, 4).map((alert, i) => (
              <div key={alert.id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '7px 0',
                borderBottom: i < 3 ? '1px solid rgba(255,255,255,0.04)' : 'none',
              }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#374151', width: '14px' }}>#{i + 1}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '12px', color: '#D1D5DB', fontWeight: '500', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {alert.entity_name}
                  </div>
                  <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>
                    {alert.entity_type}
                  </div>
                </div>
                <RiskScoreBadge score={alert.risk_score} size="sm" />
              </div>
            ))}
          </div>
        </div>

        {/* Recent Alerts feed */}
        <div style={{
          background: '#13161D',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '10px',
          padding: '16px 18px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div>
              <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '13px', color: '#F1F5F9' }}>Recent Alerts</div>
              <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>LIVE STREAM</div>
            </div>
            <button
              onClick={() => onNavigate('alerts')}
              style={{
                padding: '5px 12px',
                background: 'transparent',
                border: '1px solid rgba(245,158,11,0.3)',
                borderRadius: '5px',
                color: '#F59E0B',
                fontSize: '11px',
                fontFamily: 'Inter, sans-serif',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.08)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              View All →
            </button>
          </div>
          {MOCK_ALERTS.slice(0, 4).map((alert, i) => (
            <div key={alert.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '10px 0',
              borderBottom: i < 3 ? '1px solid rgba(255,255,255,0.04)' : 'none',
              cursor: 'pointer',
            }}
            onClick={() => onNavigate('alerts')}
            >
              <div style={{
                width: '6px', height: '6px',
                borderRadius: '50%',
                background: alert.risk_score >= 8.5 ? '#EF4444' : alert.risk_score >= 7 ? '#F97316' : '#EAB308',
                flexShrink: 0,
              }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '13px', color: '#D1D5DB', fontWeight: '500' }}>{alert.entity_name}</div>
                <div style={{ fontSize: '11px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>{alert.alert_type}</div>
              </div>
              <RiskScoreBadge score={alert.risk_score} size="sm" />
              <div style={{ fontSize: '10px', color: '#374151', fontFamily: 'JetBrains Mono, monospace', width: '50px', textAlign: 'right' }}>
                {formatRelativeTime(alert.timestamp)}
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
