import React, { useEffect, useState, useRef } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface RiskGaugeProps {
  /** Risk score: 0–10 */
  score: number;
  /** Diameter of the gauge in px. Default: 120 */
  size?: number;
  /** Show the text label below (e.g. "CRITICAL"). Default: true */
  showLabel?: boolean;
  /** Show tick marks around the arc. Default: true */
  showTicks?: boolean;
  /** Accessible label for screen readers */
  ariaLabel?: string;
}

// ─── Carbon color tokens ──────────────────────────────────────────────────────

type RiskLevel = 'MINIMAL' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

interface RiskMeta {
  level: RiskLevel;
  color: string;       // foreground / glow
  trackColor: string;  // dim arc track
  bg: string;          // badge background
  border: string;      // badge border
}

function getRiskMeta(score: number): RiskMeta {
  // score is 0–10
  if (score >= 8.5) return { level: 'CRITICAL', color: '#fa4d56', trackColor: '#3d1a1c', bg: 'rgba(250,77,86,0.12)',  border: 'rgba(250,77,86,0.35)'  };
  if (score >= 6.5) return { level: 'HIGH',     color: '#ff832b', trackColor: '#3d220f', bg: 'rgba(255,131,43,0.12)', border: 'rgba(255,131,43,0.35)' };
  if (score >= 4.5) return { level: 'MODERATE', color: '#f1c21b', trackColor: '#3d310a', bg: 'rgba(241,194,27,0.12)', border: 'rgba(241,194,27,0.35)' };
  if (score >= 2.5) return { level: 'LOW',       color: '#42be65', trackColor: '#0d2b18', bg: 'rgba(66,190,101,0.12)', border: 'rgba(66,190,101,0.35)' };
  return               { level: 'MINIMAL',  color: '#78a9ff', trackColor: '#0c1d3d', bg: 'rgba(120,169,255,0.12)', border: 'rgba(120,169,255,0.35)' };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Polar → cartesian for SVG */
function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/**
 * Build an SVG arc path.
 * startDeg / endDeg are measured from the standard SVG 0° = 3 o'clock.
 */
function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const s = polar(cx, cy, r, startDeg);
  const e = polar(cx, cy, r, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}

// The gauge spans from 225° (bottom-left) to 315° (bottom-right) — a 270° sweep
const START_DEG = 135;   // 9 o'clock-ish  (225 - 90 offset, SVG 0 = right)
const END_DEG   = 45;    // 3 o'clock-ish  (but going clockwise = 135 + 270 = 405 → normalised 45 + 360 = 405)
const SWEEP     = 270;   // total degrees

// ─── Component ────────────────────────────────────────────────────────────────

const RiskGauge: React.FC<RiskGaugeProps> = ({
  score,
  size = 120,
  showLabel = true,
  showTicks = true,
  ariaLabel,
}) => {
  const clamped = Math.min(10, Math.max(0, score));
  const [animated, setAnimated] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);
  const fromRef = useRef(0);

  // Smooth eased animation on score change
  useEffect(() => {
    const from = fromRef.current;
    const to = clamped;
    const duration = 900;

    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    startRef.current = null;

    const ease = (t: number) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

    const step = (ts: number) => {
      if (!startRef.current) startRef.current = ts;
      const elapsed = ts - startRef.current;
      const t = Math.min(elapsed / duration, 1);
      setAnimated(from + (to - from) * ease(t));
      if (t < 1) rafRef.current = requestAnimationFrame(step);
      else fromRef.current = to;
    };

    rafRef.current = requestAnimationFrame(step);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [clamped]);

  const meta = getRiskMeta(clamped);

  // Geometry
  const cx = size / 2;
  const cy = size / 2;
  const strokeW = size * 0.065;       // track width scales with size
  const r = (size - strokeW * 2 - 4) / 2;

  // Arc fill
  const fillEnd = START_DEG + (animated / 10) * SWEEP;
  const trackPath = arcPath(cx, cy, r, START_DEG, START_DEG + SWEEP);
  const fillPath  = arcPath(cx, cy, r, START_DEG, fillEnd);

  // Needle
  const needleAngle = START_DEG + (animated / 10) * SWEEP;
  const needleTip   = polar(cx, cy, r - strokeW * 0.5, needleAngle);
  const needleBase  = polar(cx, cy, strokeW * 0.3, needleAngle + 180);

  // Ticks (11 ticks for 0–10)
  const ticks = Array.from({ length: 11 }, (_, i) => {
    const angle = START_DEG + (i / 10) * SWEEP;
    const inner = polar(cx, cy, r - strokeW - 2, angle);
    const outer = polar(cx, cy, r - strokeW - 2 - (i % 5 === 0 ? size * 0.055 : size * 0.03), angle);
    const isMajor = i % 5 === 0;
    return { inner, outer, isMajor, value: i };
  });

  const viewSize = size;

  return (
    <div
      role="img"
      aria-label={ariaLabel ?? `Risk score ${clamped.toFixed(1)} out of 10 — ${meta.level}`}
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 0,
        fontFamily: "'IBM Plex Mono', monospace",
      }}
    >
      <svg
        width={viewSize}
        height={viewSize}
        viewBox={`0 0 ${viewSize} ${viewSize}`}
        style={{ overflow: 'visible' }}
      >
        {/* Glow filter */}
        <defs>
          <filter id={`glow-${meta.level}`} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation={size * 0.025} result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="subtle-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation={size * 0.01} result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ── Track ── */}
        <path
          d={trackPath}
          fill="none"
          stroke="#262626"
          strokeWidth={strokeW}
          strokeLinecap="butt"
        />

        {/* ── Coloured track fill ── */}
        {animated > 0 && (
          <path
            d={fillPath}
            fill="none"
            stroke={meta.color}
            strokeWidth={strokeW}
            strokeLinecap="butt"
            filter={`url(#glow-${meta.level})`}
            style={{ opacity: 0.9 }}
          />
        )}

        {/* ── Ticks ── */}
        {showTicks && ticks.map((t) => (
          <line
            key={t.value}
            x1={t.inner.x} y1={t.inner.y}
            x2={t.outer.x} y2={t.outer.y}
            stroke={t.isMajor ? '#525252' : '#333333'}
            strokeWidth={t.isMajor ? 1.5 : 0.75}
          />
        ))}

        {/* ── Needle ── */}
        <line
          x1={needleBase.x} y1={needleBase.y}
          x2={needleTip.x}  y2={needleTip.y}
          stroke={meta.color}
          strokeWidth={size * 0.018}
          strokeLinecap="round"
          filter="url(#subtle-glow)"
        />
        {/* Needle pivot dot */}
        <circle
          cx={cx} cy={cy}
          r={size * 0.04}
          fill="#262626"
          stroke={meta.color}
          strokeWidth={1.5}
        />

        {/* ── Centre score ── */}
        <text
          x={cx}
          y={cy + size * 0.065}
          textAnchor="middle"
          fill={meta.color}
          fontSize={size * 0.195}
          fontFamily="'IBM Plex Mono', monospace"
          fontWeight="700"
          letterSpacing={-1}
        >
          {clamped % 1 === 0 ? clamped.toFixed(0) : clamped.toFixed(1)}
        </text>

        {/* ── /10 sub-label ── */}
        <text
          x={cx}
          y={cy + size * 0.14}
          textAnchor="middle"
          fill="#525252"
          fontSize={size * 0.07}
          fontFamily="'IBM Plex Mono', monospace"
          letterSpacing={1.5}
        >
          /10
        </text>

        {/* ── Start/end range labels ── */}
        {(() => {
          const startPos = polar(cx, cy, r - strokeW - size * 0.085, START_DEG);
          const endPos   = polar(cx, cy, r - strokeW - size * 0.085, START_DEG + SWEEP);
          return (
            <>
              <text x={startPos.x} y={startPos.y + 3} textAnchor="middle"
                fill="#525252" fontSize={size * 0.062}
                fontFamily="'IBM Plex Mono', monospace">0</text>
              <text x={endPos.x}   y={endPos.y + 3}   textAnchor="middle"
                fill="#525252" fontSize={size * 0.062}
                fontFamily="'IBM Plex Mono', monospace">10</text>
            </>
          );
        })()}
      </svg>

      {/* ── Risk level badge ── */}
      {showLabel && (
        <div style={{
          marginTop: -(size * 0.04),
          padding: `${size * 0.025}px ${size * 0.07}px`,
          background: meta.bg,
          border: `1px solid ${meta.border}`,
          color: meta.color,
          fontSize: size * 0.075,
          letterSpacing: size * 0.01,
          fontFamily: "'IBM Plex Mono', monospace",
          fontWeight: 500,
          lineHeight: 1.6,
          transition: 'background 0.4s, border-color 0.4s, color 0.4s',
          userSelect: 'none',
        }}>
          {meta.level}
        </div>
      )}
    </div>
  );
};

export default RiskGauge;


// ─── Usage example (remove before shipping) ───────────────────────────────────
//
// import RiskGauge from './RiskGauge';
//
// <RiskGauge score={7.4} />
// <RiskGauge score={9.2} size={160} showLabel />
// <RiskGauge score={3}   size={80}  showTicks={false} />