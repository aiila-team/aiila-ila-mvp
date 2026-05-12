import React, { useEffect, useRef, useState, useCallback } from 'react';
import client from '../api/client';

// ─── Types ────────────────────────────────────────────────────────────────────

type Source =
  | 'FIU-IND'
  | 'GSTN'
  | 'ED Portal'
  | 'NPCI'
  | 'CIBIL'
  | 'CBI'
  | 'SEBI'
  | 'MCA21'
  | 'ALL';

interface Keyword {
  id: string;
  value: string;
  category: string;
  sources: Source[];
  alert_count?: number;
  created_at?: string;
}

interface KeywordGroup {
  category: string;
  keywords: Keyword[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const ALL_SOURCES: Source[] = [
  'FIU-IND', 'GSTN', 'ED Portal', 'NPCI', 'CIBIL', 'CBI', 'SEBI', 'MCA21',
];

const SOURCE_COLORS: Record<Source, string> = {
  'FIU-IND':   '#78a9ff',
  'GSTN':      '#42be65',
  'ED Portal': '#fa4d56',
  'NPCI':      '#f1c21b',
  'CIBIL':     '#ff832b',
  'CBI':       '#be95ff',
  'SEBI':      '#3ddbd9',
  'MCA21':     '#a8a8a8',
  'ALL':       '#6f6f6f',
};

const DEFAULT_CATEGORIES = [
  'Financial Crime', 'Shell Entities', 'Hawala', 'Crypto', 'Tax Evasion', 'Fraud',
];

// ─── Mock data (remove when real API is ready) ────────────────────────────────

const MOCK_KEYWORDS: Keyword[] = [
  { id: 'k1',  value: 'layered transaction',   category: 'Financial Crime', sources: ['FIU-IND', 'NPCI'],    alert_count: 42, created_at: '2024-01-10T10:00:00Z' },
  { id: 'k2',  value: 'smurfing',              category: 'Financial Crime', sources: ['FIU-IND'],            alert_count: 18, created_at: '2024-01-11T10:00:00Z' },
  { id: 'k3',  value: 'shell company',         category: 'Shell Entities',  sources: ['MCA21', 'ED Portal'], alert_count: 73, created_at: '2024-01-12T10:00:00Z' },
  { id: 'k4',  value: 'beneficial owner',      category: 'Shell Entities',  sources: ['MCA21'],              alert_count: 29, created_at: '2024-01-13T10:00:00Z' },
  { id: 'k5',  value: 'hundi',                 category: 'Hawala',          sources: ['FIU-IND', 'CBI'],     alert_count: 61, created_at: '2024-01-14T10:00:00Z' },
  { id: 'k6',  value: 'angadia',               category: 'Hawala',          sources: ['CBI'],                alert_count: 8,  created_at: '2024-01-15T10:00:00Z' },
  { id: 'k7',  value: 'USDT transfer',         category: 'Crypto',          sources: ['FIU-IND'],            alert_count: 34, created_at: '2024-01-16T10:00:00Z' },
  { id: 'k8',  value: 'crypto mixer',          category: 'Crypto',          sources: ['FIU-IND', 'ED Portal'],alert_count: 22, created_at: '2024-01-17T10:00:00Z' },
  { id: 'k9',  value: 'GST mismatch',          category: 'Tax Evasion',     sources: ['GSTN', 'CBI'],        alert_count: 55, created_at: '2024-01-18T10:00:00Z' },
  { id: 'k10', value: 'under-reported income', category: 'Tax Evasion',     sources: ['GSTN', 'SEBI'],       alert_count: 37, created_at: '2024-01-19T10:00:00Z' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function groupByCategory(keywords: Keyword[]): KeywordGroup[] {
  const map = new Map<string, Keyword[]>();
  keywords.forEach((kw) => {
    const cat = kw.category || 'Uncategorised';
    if (!map.has(cat)) map.set(cat, []);
    map.get(cat)!.push(kw);
  });
  return Array.from(map.entries()).map(([category, kws]) => ({ category, keywords: kws }));
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const SourcePill: React.FC<{
  source: Source;
  active: boolean;
  onClick?: () => void;
  small?: boolean;
}> = ({ source, active, onClick, small }) => {
  const color = SOURCE_COLORS[source] ?? '#6f6f6f';
  return (
    <button
      onClick={onClick}
      style={{
        padding: small ? '1px 6px' : '2px 8px',
        fontSize: small ? 9 : 10,
        fontFamily: "'IBM Plex Mono', monospace",
        letterSpacing: 0.8,
        border: `1px solid ${active ? color : '#393939'}`,
        background: active ? `${color}1a` : 'transparent',
        color: active ? color : '#525252',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
        lineHeight: 1.6,
      }}
    >
      {source}
    </button>
  );
};

// Inline edit row
const KeywordRow: React.FC<{
  kw: Keyword;
  onDelete: (id: string) => void;
  onUpdate: (id: string, patch: Partial<Keyword>) => Promise<void>;
}> = ({ kw, onDelete, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(kw.value);
  const [editSources, setEditSources] = useState<Source[]>(kw.sources);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const save = async () => {
    if (!editValue.trim()) return;
    setSaving(true);
    await onUpdate(kw.id, { value: editValue.trim(), sources: editSources });
    setSaving(false);
    setEditing(false);
  };

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const toggleSource = (s: Source) => {
    setEditSources((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  };

  return (
    <div style={{
      borderBottom: '1px solid #262626',
      transition: 'background 0.1s',
    }}>
      {editing ? (
        /* ── Edit mode ── */
        <div style={{ padding: '10px 16px', background: '#222222' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <input
              ref={inputRef}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false); }}
              style={{
                flex: 1,
                background: '#262626',
                border: '1px solid #4d4d4d',
                color: '#f4f4f4',
                padding: '5px 10px',
                fontSize: 13,
                fontFamily: "'IBM Plex Mono', monospace",
                outline: 'none',
              }}
            />
            <button onClick={save} disabled={saving} style={{
              padding: '5px 14px', fontSize: 11,
              fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.8,
              background: saving ? '#393939' : '#0f62fe',
              color: '#fff', border: 'none', cursor: 'pointer',
            }}>
              {saving ? '…' : 'SAVE'}
            </button>
            <button onClick={() => setEditing(false)} style={{
              padding: '5px 10px', fontSize: 11,
              fontFamily: "'IBM Plex Mono', monospace",
              background: 'transparent', color: '#6f6f6f',
              border: '1px solid #393939', cursor: 'pointer',
            }}>
              CANCEL
            </button>
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", alignSelf: 'center', marginRight: 4 }}>
              SOURCES:
            </span>
            {ALL_SOURCES.map((s) => (
              <SourcePill key={s} source={s} active={editSources.includes(s)} onClick={() => toggleSource(s)} />
            ))}
          </div>
        </div>
      ) : (
        /* ── View mode ── */
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '9px 16px',
        }}>
          {/* Keyword value */}
          <span style={{
            flex: 1, fontSize: 13, color: '#f4f4f4',
            fontFamily: "'IBM Plex Mono', monospace",
          }}>
            {kw.value}
          </span>

          {/* Sources */}
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {kw.sources.map((s) => (
              <SourcePill key={s} source={s} active small />
            ))}
          </div>

          {/* Alert count */}
          {kw.alert_count !== undefined && (
            <span style={{
              minWidth: 60, textAlign: 'right',
              fontSize: 11, color: '#525252',
              fontFamily: "'IBM Plex Mono', monospace",
            }}>
              {kw.alert_count} alerts
            </span>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 6, marginLeft: 8 }}>
            <button onClick={() => setEditing(true)} style={{
              fontSize: 10, padding: '2px 8px',
              fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.8,
              background: 'transparent', color: '#78a9ff',
              border: '1px solid #393939', cursor: 'pointer',
              transition: 'border-color 0.15s',
            }}>
              EDIT
            </button>
            <button onClick={() => onDelete(kw.id)} style={{
              fontSize: 10, padding: '2px 8px',
              fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.8,
              background: 'transparent', color: '#fa4d56',
              border: '1px solid #393939', cursor: 'pointer',
              transition: 'border-color 0.15s',
            }}>
              DEL
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Collapsible group section
const GroupSection: React.FC<{
  group: KeywordGroup;
  onDelete: (id: string) => void;
  onUpdate: (id: string, patch: Partial<Keyword>) => Promise<void>;
}> = ({ group, onDelete, onUpdate }) => {
  const [open, setOpen] = useState(true);

  return (
    <div style={{ border: '1px solid #262626', marginBottom: 1 }}>
      {/* Group header */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 10,
          padding: '8px 16px',
          background: '#1c1c1c', border: 'none', cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span style={{
          fontSize: 10, color: open ? '#f4f4f4' : '#6f6f6f',
          fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5,
          transition: 'color 0.15s',
        }}>
          {open ? '▾' : '▸'} {group.category.toUpperCase()}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: 10, color: '#525252',
          fontFamily: "'IBM Plex Mono', monospace",
        }}>
          {group.keywords.length} {group.keywords.length === 1 ? 'KEYWORD' : 'KEYWORDS'}
        </span>
        <span style={{
          fontSize: 10, color: '#525252',
          fontFamily: "'IBM Plex Mono', monospace",
        }}>
          {group.keywords.reduce((sum, k) => sum + (k.alert_count ?? 0), 0)} ALERTS
        </span>
      </button>

      {/* Rows */}
      {open && (
        <div style={{ background: '#161616' }}>
          {group.keywords.map((kw) => (
            <KeywordRow key={kw.id} kw={kw} onDelete={onDelete} onUpdate={onUpdate} />
          ))}
        </div>
      )}
    </div>
  );
};

// ─── Add Keyword Drawer ───────────────────────────────────────────────────────

const AddKeywordPanel: React.FC<{
  onAdd: (kw: Omit<Keyword, 'id' | 'alert_count' | 'created_at'>) => Promise<void>;
  existingCategories: string[];
}> = ({ onAdd, existingCategories }) => {
  const [value, setValue] = useState('');
  const [category, setCategory] = useState('');
  const [customCategory, setCustomCategory] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const allCats = Array.from(new Set([...DEFAULT_CATEGORIES, ...existingCategories]));

  const toggleSource = (s: Source) => {
    setSources((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  };

  const finalCategory = category === '__custom__' ? customCategory.trim() : category;

  const submit = async () => {
    if (!value.trim()) { setError('Keyword value is required'); return; }
    if (!finalCategory) { setError('Category is required'); return; }
    setError(null);
    setSubmitting(true);
    try {
      await onAdd({ value: value.trim(), category: finalCategory, sources });
      setValue(''); setCategory(''); setCustomCategory(''); setSources([]);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } catch {
      setError('Failed to add keyword');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ border: '1px solid #393939', background: '#1c1c1c', padding: '16px 20px' }}>
      {/* Title row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <span style={{ fontSize: 11, color: '#6f6f6f', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5 }}>
          ADD KEYWORD
        </span>
        {success && (
          <span style={{ fontSize: 10, color: '#42be65', fontFamily: "'IBM Plex Mono', monospace", marginLeft: 'auto' }}>
            ✓ ADDED
          </span>
        )}
        {error && (
          <span style={{ fontSize: 10, color: '#fa4d56', fontFamily: "'IBM Plex Mono', monospace", marginLeft: 'auto' }}>
            {error}
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
        {/* Keyword input */}
        <div>
          <label style={{ display: 'block', fontSize: 10, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1, marginBottom: 4 }}>
            KEYWORD / PHRASE *
          </label>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            placeholder="e.g. layered transaction"
            style={{
              width: '100%', background: '#262626',
              border: '1px solid #393939', color: '#f4f4f4',
              padding: '7px 10px', fontSize: 13,
              fontFamily: "'IBM Plex Mono', monospace",
              outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Category */}
        <div>
          <label style={{ display: 'block', fontSize: 10, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1, marginBottom: 4 }}>
            CATEGORY *
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{
              width: '100%', background: '#262626',
              border: '1px solid #393939', color: category ? '#f4f4f4' : '#525252',
              padding: '7px 10px', fontSize: 12,
              fontFamily: "'IBM Plex Mono', monospace",
              outline: 'none', appearance: 'none', boxSizing: 'border-box',
              cursor: 'pointer',
            }}
          >
            <option value="">Select category…</option>
            {allCats.map((c) => <option key={c} value={c}>{c}</option>)}
            <option value="__custom__">+ Custom…</option>
          </select>
        </div>
      </div>

      {/* Custom category input */}
      {category === '__custom__' && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontSize: 10, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1, marginBottom: 4 }}>
            CUSTOM CATEGORY NAME
          </label>
          <input
            value={customCategory}
            onChange={(e) => setCustomCategory(e.target.value)}
            placeholder="e.g. Insider Trading"
            style={{
              width: '100%', background: '#262626',
              border: '1px solid #393939', color: '#f4f4f4',
              padding: '7px 10px', fontSize: 13,
              fontFamily: "'IBM Plex Mono', monospace",
              outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>
      )}

      {/* Source assignment */}
      <div style={{ marginBottom: 14 }}>
        <label style={{ display: 'block', fontSize: 10, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1, marginBottom: 6 }}>
          ASSIGN TO SOURCES (multi-select)
        </label>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {ALL_SOURCES.map((s) => (
            <SourcePill key={s} source={s} active={sources.includes(s)} onClick={() => toggleSource(s)} />
          ))}
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={submit}
        disabled={submitting || !value.trim() || !finalCategory}
        style={{
          padding: '8px 20px',
          fontSize: 11, letterSpacing: 1,
          fontFamily: "'IBM Plex Mono', monospace",
          background: submitting || !value.trim() || !finalCategory ? '#393939' : '#0f62fe',
          color: submitting || !value.trim() || !finalCategory ? '#525252' : '#fff',
          border: 'none', cursor: submitting || !value.trim() || !finalCategory ? 'not-allowed' : 'pointer',
          transition: 'background 0.15s',
        }}
      >
        {submitting ? 'ADDING…' : '+ ADD KEYWORD'}
      </button>
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────

const KeywordManager: React.FC = () => {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterSource, setFilterSource] = useState<Source | 'ALL'>('ALL');

  // ── Fetch ──
  const fetchKeywords = useCallback(async () => {
    setIsLoading(true);
    setGlobalError(null);
    try {
      const { data } = await client.get<{ items: Keyword[] }>('/api/v1/keywords');
      setKeywords(data.items ?? []);
    } catch {
      // Fallback to mock data in dev
      setKeywords(MOCK_KEYWORDS);
      // setGlobalError('Failed to load keywords');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchKeywords(); }, [fetchKeywords]);

  // ── Add ──
  const handleAdd = async (payload: Omit<Keyword, 'id' | 'alert_count' | 'created_at'>) => {
    const { data } = await client.post<Keyword>('/api/v1/keywords', {
      value: payload.value,
      category: payload.category,
      sources: payload.sources,
    });
    setKeywords((prev) => [data, ...prev]);
  };

  // ── Delete ──
  const handleDelete = async (id: string) => {
    try {
      await client.delete(`/api/v1/keywords/${id}`);
      setKeywords((prev) => prev.filter((k) => k.id !== id));
    } catch {
      setGlobalError('Delete failed');
    }
  };

  // ── Update ──
  const handleUpdate = async (id: string, patch: Partial<Keyword>) => {
    const { data } = await client.patch<Keyword>(`/api/v1/keywords/${id}`, patch);
    setKeywords((prev) => prev.map((k) => (k.id === id ? { ...k, ...data } : k)));
  };

  // ── Filter ──
  const filtered = keywords.filter((kw) => {
    const matchSearch = !search || kw.value.toLowerCase().includes(search.toLowerCase()) || kw.category.toLowerCase().includes(search.toLowerCase());
    const matchSource = filterSource === 'ALL' || kw.sources.includes(filterSource);
    return matchSearch && matchSource;
  });

  const groups = groupByCategory(filtered);
  const totalAlerts = keywords.reduce((s, k) => s + (k.alert_count ?? 0), 0);
  const existingCategories = Array.from(new Set(keywords.map((k) => k.category)));

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #161616; }
        ::-webkit-scrollbar-thumb { background: #393939; }
        input::placeholder { color: #525252; }
        input:focus { border-color: #0f62fe !important; }
        select option { background: #262626; color: #f4f4f4; }
        .kw-row:hover { background: #1e1e1e !important; }
        .src-filter-btn:hover { border-color: #525252 !important; color: #a8a8a8 !important; }
      `}</style>

      <div style={{
        background: '#161616', minHeight: '100vh',
        color: '#f4f4f4', fontFamily: "'IBM Plex Sans', sans-serif",
        padding: '24px 32px', maxWidth: 920,
      }}>

        {/* ── Page header ── */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 10, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5 }}>
                  CONFIGURATION
                </span>
                <span style={{ color: '#393939' }}>/</span>
                <span style={{ fontSize: 10, color: '#6f6f6f', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5 }}>
                  KEYWORD MANAGER
                </span>
              </div>
              <h1 style={{ fontSize: 20, fontWeight: 600, color: '#f4f4f4', letterSpacing: -0.3 }}>
                Keyword Manager
              </h1>
              <p style={{ fontSize: 13, color: '#6f6f6f', marginTop: 4 }}>
                Manage tracked keywords, assign source systems, organise by threat category.
              </p>
            </div>

            {/* Stats strip */}
            <div style={{ display: 'flex', gap: 1, border: '1px solid #262626' }}>
              {[
                { label: 'KEYWORDS',   value: keywords.length },
                { label: 'GROUPS',     value: groupByCategory(keywords).length },
                { label: 'TTL ALERTS', value: totalAlerts },
              ].map(({ label, value }, i) => (
                <div key={label} style={{
                  padding: '8px 16px',
                  background: '#1c1c1c',
                  borderRight: i < 2 ? '1px solid #262626' : 'none',
                  textAlign: 'center',
                }}>
                  <p style={{ fontSize: 9, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5 }}>{label}</p>
                  <p style={{ fontSize: 18, fontWeight: 700, color: '#f4f4f4', fontFamily: "'IBM Plex Mono', monospace" }}>{value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {globalError && (
          <div style={{
            padding: '8px 14px', marginBottom: 16,
            background: 'rgba(250,77,86,0.1)', border: '1px solid rgba(250,77,86,0.3)',
            fontSize: 12, color: '#fa4d56', fontFamily: "'IBM Plex Mono', monospace",
          }}>
            ⚠ {globalError}
          </div>
        )}

        {/* ── Add keyword panel ── */}
        <AddKeywordPanel onAdd={handleAdd} existingCategories={existingCategories} />

        <div style={{ height: 20 }} />

        {/* ── Filters ── */}
        <div style={{
          display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap',
          marginBottom: 12,
        }}>
          {/* Search */}
          <div style={{ position: 'relative', flex: '0 0 240px' }}>
            <span style={{
              position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)',
              fontSize: 12, color: '#525252', pointerEvents: 'none',
            }}>⌕</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search keywords…"
              style={{
                width: '100%', background: '#1c1c1c',
                border: '1px solid #393939', color: '#f4f4f4',
                padding: '6px 10px 6px 26px', fontSize: 12,
                fontFamily: "'IBM Plex Mono', monospace", outline: 'none',
              }}
            />
          </div>

          {/* Source filter pills */}
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            <button
              className="src-filter-btn"
              onClick={() => setFilterSource('ALL')}
              style={{
                padding: '3px 10px', fontSize: 10,
                fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.8,
                border: `1px solid ${filterSource === 'ALL' ? '#f4f4f4' : '#393939'}`,
                background: 'transparent',
                color: filterSource === 'ALL' ? '#f4f4f4' : '#525252',
                cursor: 'pointer', transition: 'all 0.15s',
              }}
            >
              ALL
            </button>
            {ALL_SOURCES.map((s) => {
              const active = filterSource === s;
              const color = SOURCE_COLORS[s];
              return (
                <button
                  key={s}
                  className="src-filter-btn"
                  onClick={() => setFilterSource(active ? 'ALL' : s)}
                  style={{
                    padding: '3px 10px', fontSize: 10,
                    fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.8,
                    border: `1px solid ${active ? color : '#393939'}`,
                    background: active ? `${color}1a` : 'transparent',
                    color: active ? color : '#525252',
                    cursor: 'pointer', transition: 'all 0.15s',
                  }}
                >
                  {s}
                </button>
              );
            })}
          </div>

          {/* Result count */}
          {(search || filterSource !== 'ALL') && (
            <span style={{
              marginLeft: 'auto', fontSize: 10, color: '#525252',
              fontFamily: "'IBM Plex Mono', monospace",
            }}>
              {filtered.length} / {keywords.length} SHOWN
            </span>
          )}
        </div>

        {/* ── Keyword groups ── */}
        {isLoading ? (
          <div style={{ padding: 32, fontSize: 12, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1 }}>
            LOADING KEYWORDS…
          </div>
        ) : groups.length === 0 ? (
          <div style={{
            padding: 32, textAlign: 'center',
            border: '1px solid #262626', background: '#1c1c1c',
            fontSize: 12, color: '#525252', fontFamily: "'IBM Plex Mono', monospace",
          }}>
            {search || filterSource !== 'ALL' ? 'NO KEYWORDS MATCH CURRENT FILTERS' : 'NO KEYWORDS CONFIGURED — ADD ONE ABOVE'}
          </div>
        ) : (
          <div>
            {groups.map((g) => (
              <GroupSection key={g.category} group={g} onDelete={handleDelete} onUpdate={handleUpdate} />
            ))}
          </div>
        )}

        <div style={{ height: 48 }} />
      </div>
    </>
  );
};

export default KeywordManager;