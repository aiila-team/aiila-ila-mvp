import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import './index.css';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AlertInbox from './pages/AlertInbox';
import EntityProfile from './pages/EntityProfile';
import EntitiesPage from './pages/EntitiesPage';
import KeywordManager from './pages/KeywordManager';
import SourceMonitor from './pages/SourceMonitor';
import Investigation from './pages/Investigation';

// Components
import Sidebar from './components/Sidebar';
import TopNav from './components/TopNav';

// Store
import { useAuthStore } from './store';

// ─── Protected Layout ───────────────────────────────────────────────────────────
const ProtectedLayout: React.FC = () => {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="flex h-screen bg-slate-950 text-white overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/alerts" element={<AlertInbox />} />
          <Route path="/entities" element={<EntitiesPage />} />
          <Route path="/entities/:id" element={<EntityProfile />} />
          <Route path="/investigations" element={<Investigation />} />
          <Route path="/sources" element={<SourceMonitor />} />
          <Route path="/keywords" element={<KeywordManager />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
