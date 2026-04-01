import React, { useState, useEffect } from 'react';

const api = window.electronAPI;

export default function TitleBar() {
  const [maximized, setMaximized] = useState(false);

  useEffect(() => {
    api.window.isMaximized().then(setMaximized);
  }, []);

  return (
    <div style={styles.titleBar}>
      <div style={styles.dragArea}>
        <div style={styles.logo}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
          <span style={styles.title}>MineContext Hub</span>
        </div>
      </div>
      <div style={styles.controls}>
        <button style={styles.btn} onClick={() => api.window.minimize()} title="最小化">
          <svg width="12" height="12" viewBox="0 0 12 12"><rect y="5" width="12" height="1.5" fill="currentColor" rx="0.5"/></svg>
        </button>
        <button style={styles.btn} onClick={async () => { await api.window.maximize(); setMaximized(m => !m); }} title={maximized ? "还原" : "最大化"}>
          {maximized ? (
            <svg width="12" height="12" viewBox="0 0 12 12"><rect x="2" y="0" width="8" height="8" fill="none" stroke="currentColor" strokeWidth="1.2" rx="1"/><rect x="0" y="3" width="8" height="8" fill="var(--bg-primary)" stroke="currentColor" strokeWidth="1.2" rx="1"/></svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12"><rect x="1" y="1" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="1.2" rx="1.5"/></svg>
          )}
        </button>
        <button style={{...styles.btn, ...styles.closeBtn}} onClick={() => api.window.close()} title="关闭">
          <svg width="12" height="12" viewBox="0 0 12 12"><path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
        </button>
      </div>
    </div>
  );
}

const styles = {
  titleBar: {
    height: 38,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border)',
    WebkitAppRegion: 'drag',
    flexShrink: 0,
  },
  dragArea: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    paddingLeft: 14,
    height: '100%',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: 'var(--accent)',
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
    letterSpacing: '0.02em',
  },
  controls: {
    display: 'flex',
    alignItems: 'center',
    height: '100%',
    WebkitAppRegion: 'no-drag',
  },
  btn: {
    width: 46,
    height: 38,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
    background: 'transparent',
    color: 'var(--text-secondary)',
    transition: 'background 0.15s, color 0.15s',
    cursor: 'pointer',
  },
  closeBtn: {
    ':hover': {
      background: 'var(--red)',
      color: '#fff',
    },
  },
};
