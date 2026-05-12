import React, { useEffect, useState } from 'react';
import client from '../api/client';
import { Source, SourceStatus } from '../types';

const statusColors: Record<SourceStatus, string> = {
  active: 'text-green-400 bg-green-900/30',
  inactive: 'text-slate-400 bg-slate-800',
  error: 'text-red-400 bg-red-900/30',
  rate_limited: 'text-yellow-400 bg-yellow-900/20',
};

const SourceMonitor: React.FC = () => {
  const [sources, setSources] = useState<Source[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data } = await client.get<{ items: Source[] }>('/sources');
        setSources(data.items ?? []);
      } catch {
        setError('Failed to load sources');
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, []);

  const toggleSource = async (source: Source) => {
    const newStatus: SourceStatus = source.status === 'active' ? 'inactive' : 'active';
    try {
      await client.patch(`/sources/${source.id}`, { status: newStatus });
      setSources((prev) =>
        prev.map((s) => (s.id === source.id ? { ...s, status: newStatus } : s))
      );
    } catch {
      // silent
    }
  };

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Source Monitor</h1>
        <p className="text-slate-400 text-sm mt-0.5">Monitor and manage data collection sources</p>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {isLoading ? (
        <p className="text-slate-500 text-sm">Loading…</p>
      ) : (
        <div className="space-y-2">
          {sources.length === 0 && (
            <p className="text-slate-500 text-sm">No sources configured</p>
          )}
          {sources.map((source) => (
            <div
              key={source.id}
              className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 flex items-center justify-between gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-white font-medium text-sm truncate">{source.name}</h3>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[source.status]}`}
                  >
                    {source.status}
                  </span>
                </div>
                <p className="text-slate-500 text-xs mt-0.5 truncate">{source.url}</p>
                {source.error_message && (
                  <p className="text-red-400 text-xs mt-1">{source.error_message}</p>
                )}
                {source.last_checked && (
                  <p className="text-slate-600 text-xs mt-0.5">
                    Checked: {new Date(source.last_checked).toLocaleString()}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500 capitalize">{source.type}</span>
                <button
                  onClick={() => toggleSource(source)}
                  className={`text-xs px-3 py-1 rounded-lg border transition-colors font-medium ${
                    source.status === 'active'
                      ? 'border-red-700 text-red-400 hover:bg-red-900/20'
                      : 'border-green-700 text-green-400 hover:bg-green-900/20'
                  }`}
                >
                  {source.status === 'active' ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SourceMonitor;
