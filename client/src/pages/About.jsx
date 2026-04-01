import React, { useState, useEffect } from 'react';

const api = window.electronAPI;

export default function About() {
  const [version, setVersion] = useState('');

  useEffect(() => {
    api.app.getVersion().then(setVersion);
  }, []);

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.pageTitle}>关于</h1>
        <p style={styles.pageDesc}>MineContext Hub 桌面客户端</p>
      </div>

      <div style={styles.card}>
        <div style={styles.logoSection}>
          <div style={styles.logoCircle}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div>
            <h2 style={styles.appName}>MineContext Hub</h2>
            <div style={styles.versionBadge}>v{version || '1.0.0'}</div>
          </div>
        </div>

        <p style={styles.description}>
          将 MineContext 桌面端采集的上下文数据自动同步到云端 Context Hub。
          支持增量同步、批量推送、多数据类型管理，在后台静默运行，为你的 AI 工作流提供持续的数据支撑。
        </p>

        <div style={styles.divider} />

        <div style={styles.infoGrid}>
          <div style={styles.infoItem}>
            <div style={styles.infoLabel}>技术栈</div>
            <div style={styles.infoValue}>Electron + React + Node.js</div>
          </div>
          <div style={styles.infoItem}>
            <div style={styles.infoLabel}>协议</div>
            <div style={styles.infoValue}>MIT License</div>
          </div>
          <div style={styles.infoItem}>
            <div style={styles.infoLabel}>数据库</div>
            <div style={styles.infoValue}>SQLite (better-sqlite3)</div>
          </div>
          <div style={styles.infoItem}>
            <div style={styles.infoLabel}>服务端</div>
            <div style={styles.infoValue}>FastAPI + SQLite</div>
          </div>
        </div>

        <div style={styles.divider} />

        <div style={styles.links}>
          <button
            style={styles.linkBtn}
            onClick={() => api.app.openExternal('https://github.com/XimilalaXiang/MineContext-Hub')}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--bg-input)'}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            GitHub 仓库
          </button>
          <button
            style={styles.linkBtn}
            onClick={() => api.app.openExternal('https://github.com/volcengine/MineContext')}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--bg-input)'}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
            </svg>
            MineContext 项目
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  header: {
    marginBottom: 24,
  },
  pageTitle: {
    fontSize: 22,
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.01em',
  },
  pageDesc: {
    fontSize: 13,
    color: 'var(--text-secondary)',
    marginTop: 4,
  },
  card: {
    background: 'var(--bg-card)',
    borderRadius: 12,
    padding: 28,
    border: '1px solid var(--border)',
  },
  logoSection: {
    display: 'flex',
    alignItems: 'center',
    gap: 18,
    marginBottom: 20,
  },
  logoCircle: {
    width: 64,
    height: 64,
    borderRadius: 16,
    background: 'rgba(59,130,246,0.1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid rgba(59,130,246,0.2)',
  },
  appName: {
    fontSize: 20,
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
  versionBadge: {
    display: 'inline-block',
    marginTop: 4,
    padding: '2px 10px',
    background: 'rgba(59,130,246,0.1)',
    border: '1px solid rgba(59,130,246,0.2)',
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--accent)',
  },
  description: {
    fontSize: 14,
    lineHeight: 1.7,
    color: 'var(--text-secondary)',
  },
  divider: {
    height: 1,
    background: 'var(--border)',
    margin: '20px 0',
  },
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 14,
  },
  infoItem: {
    padding: '12px 14px',
    background: 'var(--bg-input)',
    borderRadius: 8,
  },
  infoLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 13,
    color: 'var(--text-primary)',
    fontWeight: 500,
  },
  links: {
    display: 'flex',
    gap: 10,
  },
  linkBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 16px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text-primary)',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
};
