import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, useUIStore } from '../store';
import SearchBar from './SearchBar';

const TopNav: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { toggleSidebar } = useUIStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="flex items-center gap-4 px-4 py-3 bg-slate-900 border-b border-slate-800 h-14">
      <button
        onClick={toggleSidebar}
        className="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded"
        aria-label="Toggle sidebar"
      >
        ☰
      </button>

      <div className="flex-1 max-w-md">
        <SearchBar />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-sky-600 flex items-center justify-center text-white text-xs font-bold">
            {user?.username?.[0]?.toUpperCase() ?? 'A'}
          </div>
          <div className="hidden sm:block">
            <p className="text-xs text-white font-medium">{user?.username ?? 'Analyst'}</p>
            <p className="text-xs text-slate-500">{user?.role ?? 'analyst'}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="text-xs text-slate-400 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-slate-800"
        >
          Logout
        </button>
      </div>
    </header>
  );
};

export default TopNav;
