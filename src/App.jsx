import { useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import Login from './pages/Login.jsx';
import DashboardHome from './pages/Dashboard.jsx';
import AlertInbox from './pages/AlertInbox.jsx';
import KeywordManager from './pages/KeywordManager.jsx';
import SourceMonitor from './pages/SourceMonitor.jsx';
import GraphView from './pages/GraphView.jsx';

function PlaceholderPage({ title }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '12px', color: '#374151' }}>
      <div style={{ fontSize: '32px', opacity: 0.2 }}>◈</div>
      <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '16px', color: '#4B5563' }}>{title}</div>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#2E3340' }}>COMING — DAY 3</div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('dashboard');

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  const renderPage = () => {
    switch (page) {
      case 'dashboard': return <DashboardHome onNavigate={setPage} />;
      case 'alerts': return <AlertInbox />;
      case 'keywords': return <KeywordManager />;
      case 'sources': return <SourceMonitor />;
      case 'graph': return <GraphView />;
      case 'entities': return <PlaceholderPage title="Entity List" />;
      default: return <DashboardHome onNavigate={setPage} />;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar activePage={page} onNavigate={setPage} />
      <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', background: '#07080A' }}>
        {renderPage()}
      </main>
    </div>
  );
}