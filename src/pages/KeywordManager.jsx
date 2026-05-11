import { useState } from 'react';
import TopNav from '../components/TopNav.jsx';
import { MOCK_KEYWORDS } from '../mockData.js';

const GROUPS = ['Financial Crime', 'Identity Fraud', 'Cyber Crime', 'Terrorism', 'Narcotics'];

export default function KeywordManager() {
  const [keywords, setKeywords] = useState(MOCK_KEYWORDS);
  const [newWord, setNewWord] = useState('');
  const [newGroup, setNewGroup] = useState('Financial Crime');
  const [adding, setAdding] = useState(false);

  const toggleEnabled = (id) => {
    setKeywords(prev => prev.map(k => k.id === id ? { ...k, enabled: !k.enabled } : k));
  };

  const deleteKeyword = (id) => {
    setKeywords(prev => prev.filter(k => k.id !== id));
  };

  const addKeyword = () => {
    if (!newWord.trim()) return;
    setKeywords(prev => [
      ...prev,
      { id: `kw-${Date.now()}`, word: newWord.trim(), group: newGroup, hits_today: 0, enabled: true }
    ]);
    setNewWord('');
    setAdding(false);
  };

  const groups = [...new Set(keywords.map(k => k.group))];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <TopNav title="Keyword Manager" subtitle={`${keywords.filter(k => k.enabled).length} ACTIVE KEYWORDS`} />

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
        {/* Add keyword */}
        <div style={{
          background: '#13161D',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '10px',
          padding: '16px 18px',
          marginBottom: '20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: adding ? '14px' : '0' }}>
            <div>
              <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '13px', color: '#F1F5F9' }}>Add Keyword</div>
              <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>TRIGGER ON KEYWORD MATCH</div>
            </div>
            {!adding && (
              <button
                onClick={() => setAdding(true)}
                style={{
                  padding: '7px 14px',
                  background: 'rgba(245,158,11,0.1)',
                  border: '1px solid rgba(245,158,11,0.3)',
                  borderRadius: '6px',
                  color: '#F59E0B',
                  fontSize: '12px',
                  fontFamily: 'Inter, sans-serif',
                  fontWeight: '500',
                  cursor: 'pointer',
                }}
              >+ Add Keyword</button>
            )}
          </div>
          {adding && (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                value={newWord}
                onChange={e => setNewWord(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addKeyword()}
                placeholder="Enter keyword or phrase..."
                autoFocus
                style={{
                  flex: 2,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(245,158,11,0.3)',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '13px',
                  color: '#D1D5DB',
                  fontFamily: 'Inter, sans-serif',
                  outline: 'none',
                }}
              />
              <select
                value={newGroup}
                onChange={e => setNewGroup(e.target.value)}
                style={{
                  flex: 1,
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '6px',
                  color: '#9CA3AF',
                  fontSize: '12px',
                  fontFamily: 'Inter, sans-serif',
                  padding: '8px',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                {GROUPS.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
              <button
                onClick={addKeyword}
                style={{
                  padding: '8px 16px',
                  background: 'rgba(245,158,11,0.12)',
                  border: '1px solid rgba(245,158,11,0.3)',
                  borderRadius: '6px',
                  color: '#F59E0B',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontFamily: 'Inter, sans-serif',
                }}
              >Add</button>
              <button
                onClick={() => setAdding(false)}
                style={{
                  padding: '8px',
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '6px',
                  color: '#6B7280',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >Cancel</button>
            </div>
          )}
        </div>

        {/* Keywords by group */}
        {groups.map(group => {
          const groupKws = keywords.filter(k => k.group === group);
          return (
            <div key={group} style={{ marginBottom: '16px' }}>
              <div style={{
                fontSize: '10px',
                color: '#4B5563',
                fontFamily: 'JetBrains Mono, monospace',
                letterSpacing: '0.06em',
                marginBottom: '8px',
                paddingLeft: '4px',
              }}>{group.toUpperCase()} — {groupKws.length} KEYWORDS</div>

              <div style={{
                background: '#13161D',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '10px',
                overflow: 'hidden',
              }}>
                {groupKws.map((kw, i) => (
                  <div key={kw.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 16px',
                    borderBottom: i < groupKws.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                    opacity: kw.enabled ? 1 : 0.4,
                    transition: 'opacity 0.2s',
                  }}>
                    {/* Toggle */}
                    <div
                      onClick={() => toggleEnabled(kw.id)}
                      style={{
                        width: '32px', height: '18px',
                        borderRadius: '9px',
                        background: kw.enabled ? 'rgba(245,158,11,0.4)' : 'rgba(255,255,255,0.08)',
                        cursor: 'pointer',
                        position: 'relative',
                        transition: 'background 0.2s',
                        flexShrink: 0,
                        border: kw.enabled ? '1px solid rgba(245,158,11,0.5)' : '1px solid rgba(255,255,255,0.1)',
                      }}
                    >
                      <div style={{
                        position: 'absolute',
                        top: '2px',
                        left: kw.enabled ? '14px' : '2px',
                        width: '12px', height: '12px',
                        borderRadius: '50%',
                        background: kw.enabled ? '#F59E0B' : '#4B5563',
                        transition: 'left 0.2s',
                      }} />
                    </div>

                    {/* Keyword */}
                    <span style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '13px',
                      color: '#F1F5F9',
                      flex: 1,
                    }}>{kw.word}</span>

                    {/* Hits */}
                    {kw.hits_today > 0 && (
                      <div style={{
                        padding: '2px 8px',
                        background: 'rgba(239,68,68,0.1)',
                        border: '1px solid rgba(239,68,68,0.2)',
                        borderRadius: '4px',
                        fontSize: '10px',
                        color: '#F87171',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}>
                        {kw.hits_today} hits today
                      </div>
                    )}

                    {/* Delete */}
                    <button
                      onClick={() => deleteKeyword(kw.id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#374151',
                        cursor: 'pointer',
                        fontSize: '14px',
                        padding: '4px',
                        lineHeight: 1,
                        transition: 'color 0.15s',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.color = '#EF4444'; }}
                      onMouseLeave={e => { e.currentTarget.style.color = '#374151'; }}
                    >✕</button>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
