import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '../store';

const SearchBar: React.FC = () => {
  const { searchQuery, setSearchQuery } = useUIStore();
  const [localQuery, setLocalQuery] = useState(searchQuery);
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(localQuery);
    if (localQuery.trim()) {
      navigate(`/entities?search=${encodeURIComponent(localQuery)}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
          🔍
        </span>
        <input
          type="text"
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
          placeholder="Search entities, alerts..."
          className="
            w-full bg-slate-800 border border-slate-700 rounded-lg
            pl-8 pr-3 py-1.5 text-sm text-slate-200 placeholder-slate-500
            focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/50
            transition-colors
          "
        />
      </div>
    </form>
  );
};

export default SearchBar;
