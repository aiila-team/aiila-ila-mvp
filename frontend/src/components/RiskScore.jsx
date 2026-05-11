import { getRiskLevel } from '../utils.js';

export function RiskScoreBadge({ score, size = 'md' }) {
  const risk = getRiskLevel(score);
  const sizes = {
    sm: { fontSize: '9px', padding: '2px 6px', scoreSize: '10px' },
    md: { fontSize: '10px', padding: '3px 8px', scoreSize: '12px' },
    lg: { fontSize: '11px', padding: '4px 10px', scoreSize: '14px' },
  };
  const s = sizes[size];

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '5px',
      background: risk.bg,
      border: `1px solid ${risk.border}`,
      borderRadius: '5px',
      padding: s.padding,
    }}>
      <span style={{
        fontSize: s.scoreSize,
        fontWeight: '700',
        color: risk.color,
        fontFamily: 'JetBrains Mono, monospace',
      }}>{score.toFixed(1)}</span>
      <span style={{
        fontSize: s.fontSize,
        fontWeight: '600',
        color: risk.color,
        letterSpacing: '0.08em',
        fontFamily: 'JetBrains Mono, monospace',
        opacity: 0.8,
      }}>{risk.label}</span>
    </div>
  );
}

// Circular gauge 0-10 risk score
export function RiskGauge({ score, size = 100 }) {
  const risk = getRiskLevel(score);
  const r = (size / 2) - 8;
  const circ = 2 * Math.PI * r;
  const pct = score / 10;
  const arc = circ * pct;
  // Start from bottom-left, go clockwise
  const strokeDasharray = `${arc} ${circ - arc}`;
  const rotation = -90; // start from top

  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'inline-block' }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Track */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="6"
          strokeLinecap="round"
        />
        {/* Score arc */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke={risk.color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          strokeDashoffset="0"
          transform={`rotate(${rotation} ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray 0.6s ease', filter: `drop-shadow(0 0 4px ${risk.color}60)` }}
        />
      </svg>
      {/* Center text */}
      <div style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <span style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: '700',
          fontSize: size * 0.22 + 'px',
          color: risk.color,
          lineHeight: 1,
        }}>{score.toFixed(1)}</span>
        <span style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: size * 0.1 + 'px',
          color: risk.color,
          opacity: 0.7,
          letterSpacing: '0.05em',
        }}>{risk.label}</span>
      </div>
    </div>
  );
}
