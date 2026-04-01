import React from 'react';

const NAV_ITEMS = [
  {
    id: 'dashboard',
    label: '仪表盘',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
    ),
  },
  {
    id: 'settings',
    label: '设置',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
      </svg>
    ),
  },
  {
    id: 'logs',
    label: '日志',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/>
      </svg>
    ),
  },
  {
    id: 'about',
    label: '关于',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
      </svg>
    ),
  },
];

export default function Sidebar({ current, onChange, syncStatus }) {
  const statusColor = {
    running: 'var(--green)',
    syncing: 'var(--accent)',
    stopped: 'var(--text-muted)',
    error: 'var(--red)',
  }[syncStatus?.status] || 'var(--text-muted)';

  return (
    <aside style={styles.sidebar}>
      <nav style={styles.nav}>
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            style={{
              ...styles.navItem,
              ...(current === item.id ? styles.navItemActive : {}),
            }}
            onMouseEnter={e => {
              if (current !== item.id) e.currentTarget.style.background = 'var(--bg-card)';
            }}
            onMouseLeave={e => {
              if (current !== item.id) e.currentTarget.style.background = 'transparent';
            }}
          >
            <span style={{ color: current === item.id ? 'var(--accent)' : 'var(--text-secondary)' }}>
              {item.icon}
            </span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div style={styles.statusBox}>
        <div style={styles.statusDot}>
          <span style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: statusColor,
            display: 'inline-block',
            boxShadow: `0 0 6px ${statusColor}`,
          }} />
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            {{
              running: '同步运行中',
              syncing: '正在同步...',
              stopped: '已停止',
              error: '同步异常',
            }[syncStatus?.status] || '未知'}
          </span>
        </div>
      </div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: 180,
    background: 'var(--bg-secondary)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    flexShrink: 0,
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    padding: '12px 8px',
    gap: 2,
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 12px',
    border: 'none',
    borderRadius: 8,
    background: 'transparent',
    color: 'var(--text-secondary)',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
    textAlign: 'left',
  },
  navItemActive: {
    background: 'var(--bg-card)',
    color: 'var(--text-primary)',
  },
  statusBox: {
    padding: '16px 12px',
    borderTop: '1px solid var(--border)',
  },
  statusDot: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 12px',
    background: 'var(--bg-card)',
    borderRadius: 8,
  },
};
