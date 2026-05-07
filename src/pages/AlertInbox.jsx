import { useState, useMemo } from 'react';
import AlertCard from '../components/AlertCard.jsx';
import AlertDetail from '../components/AlertDetail.jsx';
import TopNav from '../components/TopNav.jsx';
import { MOCK_ALERTS } from '../mockData.js';

const SORT_OPTIONS = [
  { value: 'risk_desc', label: 'Risk ↓' },
  { value: 'risk_asc', label: 'Risk ↑' },
  { value: 'time_desc', label: 'Newest' },
  { value: 'time_asc', label: 'Oldest' },
];

const FILTER_OPTIONS = [
  { value: 'all', label: 'All Alerts' },
  { value: 'new', label: 'New' },
  { value: 'under_review', label: 'Reviewing' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'dismissed', label: 'Dismissed' },
];

const RISK_FILTERS = [
  { value: 'all', label: 'All Risk' },
  { value: 'critical', label: 'Critical (8.5+)', min: 8.5 },
  { value: 'high', label: 'High (7-8.5)', min: 7, max: 8.5 },
  { value: 'medium', label: 'Medium (5.5-7)', min: 5.5, max: 7 },
];

export default function AlertInbox() {
  const [alerts, setAlerts] = useState(MOCK_ALERTS);
  const [selected, setSelected] = useState(null);
  const [sortBy, setSortBy] = useState('risk_desc');
  const [statusFilter, setStatusFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');

  const filtered = useMemo(() => {
    let result = [...alerts];
    if (statusFilter !== 'all') result = result.filter(a => a.status === statusFilter);
    if (riskFilter !== 'all') {
      const rf = RISK_FILTERS.find(r => r.value === riskFilter);
      result = result.filter(a => {
        if (rf.min !== undefined && a.risk_score < rf.min) return false;
        if (rf.max !== undefined && a.risk_score >= rf.max) return false;
        return true;
      });
    }
    result.sort((a, b) => {
      if (sortBy === 'risk_desc') return b.risk_score - a.risk_score;
      if (sortBy === 'risk_asc') return a.risk_score - b.risk_score;
      if (sortBy === 'time_desc') return new Date(b.timestamp) - new Date(a.timestamp);
      if (sortBy === 'time_asc') return new Date(a.timestamp) - new Date(b.timestamp);
      return 0;
    });
    return result;
  }, [alerts, statusFilter, riskFilter, sortBy]);

  const handleStatusChange = (alertId, newStatus) => {
    setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, status: newStatus } : a));
    if (selected?.id === alertId) setSelected(prev => ({ ...prev, status: newStatus }));
  };

  const counts = useMemo(() => ({
    all: alerts.length,
    new: alerts.filter(a => a.status === 'new').length,
    under_review: alerts.filter(a => a.status === 'under_review').length,
    confirmed: alerts.filter(a => a.status === 'confirmed').length,
  }), [alerts]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopNav
        title="Alert Inbox"
        subtitle={`${counts.new} UNREVIEWED · ${counts.all} TOTAL`}
      />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left: List */}
        <div style={{
          width: '420px',
          minWidth: '420px',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {/* Filter bar */}
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            background: '#0D0F14',
          }}>
            {/* Status filter tabs */}
            <div style={{ display: 'flex', gap: '4px', marginBottom: '10px', overflowX: 'auto' }}>
              {FILTER_OPTIONS.map(opt => {
                const active = statusFilter === opt.value;
                return (
                  <button
                    key={opt.value}
                    onClick={() => setStatusFilter(opt.value)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '5px',
                      border: `1px solid ${active ? 'rgba(245,158,11,0.4)' : 'rgba(255,255,255,0.06)'}`,
                      background: active ? 'rgba(245,158,11,0.1)' : 'transparent',
                      color: active ? '#F59E0B' : '#4B5563',
                      fontSize: '11px',
                      fontFamily: 'JetBrains Mono, monospace',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      transition: 'all 0.15s',
                    }}
                  >
                    {opt.label}
                    {opt.value !== 'all' && counts[opt.value] > 0 && (
                      <span style={{ marginLeft: '4px', opacity: 0.7 }}>({counts[opt.value]})</span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Sort + risk filter row */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                style={{
                  flex: 1,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '5px',
                  color: '#9CA3AF',
                  fontSize: '11px',
                  fontFamily: 'JetBrains Mono, monospace',
                  padding: '5px 8px',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <select
                value={riskFilter}
                onChange={e => setRiskFilter(e.target.value)}
                style={{
                  flex: 1,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '5px',
                  color: '#9CA3AF',
                  fontSize: '11px',
                  fontFamily: 'JetBrains Mono, monospace',
                  padding: '5px 8px',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                {RISK_FILTERS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          {/* Results count */}
          <div style={{
            padding: '8px 16px',
            fontSize: '10px',
            color: '#374151',
            fontFamily: 'JetBrains Mono, monospace',
            borderBottom: '1px solid rgba(255,255,255,0.04)',
          }}>
            SHOWING {filtered.length} OF {alerts.length} ALERTS
          </div>

          {/* Alert list */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 12px' }}>
            {filtered.length === 0 ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '200px',
                color: '#374151',
                gap: '8px',
              }}>
                <div style={{ fontSize: '24px', opacity: 0.3 }}>◎</div>
                <div style={{ fontSize: '12px', fontFamily: 'Inter, sans-serif' }}>No alerts match filters</div>
              </div>
            ) : (
              filtered.map(alert => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onClick={setSelected}
                  selected={selected?.id === alert.id}
                />
              ))
            )}
          </div>
        </div>

        {/* Right: Detail panel */}
        <div style={{
          flex: 1,
          background: '#0F1117',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {/* Detail header bar */}
          {selected && (
            <div style={{
              padding: '10px 20px',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
              background: '#0D0F14',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '10px',
              fontFamily: 'JetBrains Mono, monospace',
            }}>
              <span style={{ color: '#4B5563' }}>ALERT DETAIL</span>
              <span style={{ color: '#2E3340' }}>→</span>
              <span style={{ color: '#F59E0B' }}>{selected.id}</span>
              <button
                onClick={() => setSelected(null)}
                style={{
                  marginLeft: 'auto',
                  background: 'transparent',
                  border: 'none',
                  color: '#4B5563',
                  cursor: 'pointer',
                  fontSize: '14px',
                }}
              >✕</button>
            </div>
          )}
          <AlertDetail
            alert={selected}
            onClose={() => setSelected(null)}
            onStatusChange={handleStatusChange}
          />
        </div>
      </div>
    </div>
  );
}
