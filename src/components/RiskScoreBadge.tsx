import React from 'react';

interface RiskScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const getRiskLevel = (score: number): { label: string; color: string } => {
  if (score >= 80) return { label: 'Critical', color: 'bg-red-600 text-white' };
  if (score >= 60) return { label: 'High', color: 'bg-orange-500 text-white' };
  if (score >= 40) return { label: 'Medium', color: 'bg-yellow-500 text-black' };
  if (score >= 20) return { label: 'Low', color: 'bg-blue-500 text-white' };
  return { label: 'Minimal', color: 'bg-gray-500 text-white' };
};

const sizeClasses = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-sm px-2 py-1',
  lg: 'text-base px-3 py-1.5',
};

const RiskScoreBadge: React.FC<RiskScoreBadgeProps> = ({
  score,
  size = 'md',
  showLabel = false,
}) => {
  const { label, color } = getRiskLevel(score);
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-semibold ${color} ${sizeClasses[size]}`}
      title={`Risk Score: ${score}/100`}
    >
      <span>{score}</span>
      {showLabel && <span>· {label}</span>}
    </span>
  );
};

export default RiskScoreBadge;
