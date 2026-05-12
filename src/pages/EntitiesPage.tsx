import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { EntityType } from '../types';
import EntityCard from '../components/EntityCard';
import { useEntities } from '../hooks/useEntities';

const ENTITY_TYPES: EntityType[] = ['person', 'organization', 'domain', 'ip', 'url', 'hash'];

const EntitiesPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [filterType, setFilterType] = useState<string>('');
  const [page, setPage] = useState(1);

  const { entities, isLoading, error, total } = useEntities({
    page,
    page_size: 20,
    type: filterType || undefined,
    search: searchParams.get('search') ?? undefined,
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">Entities</h1>
          <p className="text-slate-400 text-sm">{total} total entities</p>
        </div>
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
          className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-sky-500"
        >
          <option value="">All Types</option>
          {ENTITY_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-slate-800/40 border border-slate-700 rounded-xl h-32 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {entities.map((entity) => (
            <EntityCard
              key={entity.id}
              entity={entity}
              onClick={(e) => navigate(`/entities/${e.id}`)}
            />
          ))}
        </div>
      )}

      {!isLoading && entities.length === 0 && (
        <p className="text-slate-500 text-sm text-center py-12">No entities found</p>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="text-sm px-3 py-1 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-slate-500 text-sm">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 20 >= total}
            className="text-sm px-3 py-1 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default EntitiesPage;
