import React, { useEffect, useState } from 'react';
import client from '../api/client';
import { Investigation as InvestigationType, InvestigationStatus } from '../types';

const statusColors: Record<InvestigationStatus, string> = {
  open: 'text-blue-400 bg-blue-900/30',
  in_progress: 'text-yellow-400 bg-yellow-900/20',
  closed: 'text-slate-400 bg-slate-800',
};

const Investigation: React.FC = () => {
  const [investigations, setInvestigations] = useState<InvestigationType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selected, setSelected] = useState<InvestigationType | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data } = await client.get<{ items: InvestigationType[] }>('/investigations');
        setInvestigations(data.items ?? []);
      } catch {
        // silent
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, []);

  return (
    <div className="flex h-full overflow-hidden">
      {/* List */}
      <div className="w-72 flex-shrink-0 flex flex-col border-r border-slate-800">
        <div className="p-4 border-b border-slate-800">
          <h1 className="text-sm font-bold text-white">Investigations</h1>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {isLoading && <p className="text-slate-500 text-xs p-2">Loading…</p>}
          {investigations.map((inv) => (
            <div
              key={inv.id}
              onClick={() => setSelected(inv)}
              className={`p-3 rounded-lg cursor-pointer transition-colors border ${
                selected?.id === inv.id
                  ? 'border-sky-600/50 bg-sky-900/20'
                  : 'border-slate-700 bg-slate-800/40 hover:border-slate-600'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-white text-sm font-medium leading-snug">{inv.title}</p>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded-full font-medium flex-shrink-0 ${statusColors[inv.status]}`}
                >
                  {inv.status}
                </span>
              </div>
              {inv.assignee && (
                <p className="text-slate-500 text-xs mt-1">{inv.assignee}</p>
              )}
              <p className="text-slate-600 text-xs mt-1">
                {new Date(inv.updated_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Detail */}
      <div className="flex-1 overflow-y-auto p-6">
        {selected ? (
          <div className="max-w-2xl space-y-4">
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-lg font-bold text-white">{selected.title}</h2>
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${statusColors[selected.status]}`}>
                {selected.status}
              </span>
            </div>
            {selected.description && (
              <p className="text-slate-300 text-sm leading-relaxed">{selected.description}</p>
            )}
            <div className="grid grid-cols-2 gap-3 text-xs text-slate-500">
              <p>Created: {new Date(selected.created_at).toLocaleString()}</p>
              <p>Updated: {new Date(selected.updated_at).toLocaleString()}</p>
              {selected.assignee && <p>Assignee: {selected.assignee}</p>}
              <p>Entities: {selected.entity_ids?.length ?? 0}</p>
            </div>
            <div className="flex gap-2 flex-wrap">
              {selected.tags?.map((tag) => (
                <span key={tag} className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-slate-600 text-sm">
            Select an investigation to view details
          </div>
        )}
      </div>
    </div>
  );
};

export default Investigation;
