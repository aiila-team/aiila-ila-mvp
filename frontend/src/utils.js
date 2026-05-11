export function formatRelativeTime(isoString) {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function getRiskLevel(score) {
  if (score >= 8.5) return { label: 'CRITICAL', color: '#EF4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)' };
  if (score >= 7.0) return { label: 'HIGH', color: '#F97316', bg: 'rgba(249,115,22,0.12)', border: 'rgba(249,115,22,0.3)' };
  if (score >= 5.5) return { label: 'MEDIUM', color: '#EAB308', bg: 'rgba(234,179,8,0.12)', border: 'rgba(234,179,8,0.3)' };
  return { label: 'LOW', color: '#22C55E', bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.3)' };
}

export function getEntityColor(type) {
  const map = {
    Person: '#60A5FA',
    Phone: '#34D399',
    SocialAccount: '#F59E0B',
    UPIAccount: '#A78BFA',
    Phone_Cluster: '#FB7185',
    EmailAddress: '#67E8F9',
  };
  return map[type] || '#9CA3AF';
}

export function getStatusBadge(status) {
  const map = {
    new: { label: 'NEW', color: '#EF4444', bg: 'rgba(239,68,68,0.12)' },
    under_review: { label: 'REVIEWING', color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
    confirmed: { label: 'CONFIRMED', color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
    dismissed: { label: 'DISMISSED', color: '#6B7280', bg: 'rgba(107,114,128,0.1)' },
  };
  return map[status] || map.new;
}

export function getSourceTierLabel(tier) {
  return { 1: 'T1 — Verified', 2: 'T2 — Mainstream', 3: 'T3 — Unverified', 4: 'T4 — Dark Web' }[tier] || 'Unknown';
}
