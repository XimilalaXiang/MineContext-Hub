import React, { useState, useEffect, useCallback, useRef } from 'react';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Logs from './pages/Logs';
import About from './pages/About';

const api = window.electronAPI;

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [config, setConfig] = useState(null);
  const [syncStatus, setSyncStatus] = useState({ status: 'stopped', message: '' });
  const [syncStats, setSyncStats] = useState(null);
  const [logs, setLogs] = useState([]);

  const loadConfig = useCallback(async () => {
    const cfg = await api.config.get();
    setConfig(cfg);
  }, []);

  useEffect(() => {
    loadConfig();

    api.sync.getStatus().then(s => { if (s) setSyncStatus(s); });
    api.sync.getLogs().then(l => { if (l) setLogs(l); });
    api.sync.getStats().then(s => { if (s) setSyncStats(s); });

    const offStatus = api.sync.onStatus((data) => setSyncStatus(data));
    const offLog = api.sync.onLog((entry) => {
      setLogs(prev => [entry, ...prev].slice(0, 500));
    });
    const offStats = api.sync.onStats((data) => setSyncStats(data));

    return () => { offStatus(); offLog(); offStats(); };
  }, [loadConfig]);

  const updateConfig = useCallback(async (key, value) => {
    await api.config.set(key, value);
    await loadConfig();
  }, [loadConfig]);

  const updateConfigAll = useCallback(async (cfg) => {
    await api.config.setAll(cfg);
    await loadConfig();
  }, [loadConfig]);

  if (!config) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Loading...</div>
      </div>
    );
  }

  const pageProps = {
    config,
    syncStatus,
    syncStats,
    logs,
    updateConfig,
    updateConfigAll,
    api,
  };

  return (
    <>
      <TitleBar />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar current={currentPage} onChange={setCurrentPage} syncStatus={syncStatus} />
        <main style={{ flex: 1, overflow: 'auto', padding: '24px 28px' }}>
          {currentPage === 'dashboard' && <Dashboard {...pageProps} />}
          {currentPage === 'settings' && <Settings {...pageProps} />}
          {currentPage === 'logs' && <Logs {...pageProps} />}
          {currentPage === 'about' && <About {...pageProps} />}
        </main>
      </div>
    </>
  );
}
