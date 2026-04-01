import React, { useRef, useEffect, useState } from 'react';

const LEVEL_STYLE = {
  info: { color: 'var(--accent)', bg: 'rgba(59,130,246,0.08)', label: 'INFO' },
  warn: { color: 'var(--yellow)', bg: 'rgba(245,158,11,0.08)', label: 'WARN' },
  error: { color: 'var(--red)', bg: 'rgba(239,68,68,0.08)', label: 'ERROR' },
  debug: { color: 'var(--text-muted)', bg: 'rgba(92,103,122,0.08)', label: 'DEBUG' },
};

export default function Logs({ logs }) {
  const [filter, setFilter] = useState('all');
  const listRef = useRef(null);

  const filtered = filter === 'all' ? logs : logs.filter(l => l.level === filter);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.pageTitle}>同步日志</h1>
          <p style={styles.pageDesc}>查看同步过程中的详细日志记录</p>
        </div>
        <div style={styles.filterBar}>
          {['all', 'info', 'warn', 'error'].map(level => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              style={{
                ...styles.filterBtn,
                ...(filter === level ? styles.filterBtnActive : {}),
              }}
            >
              {level === 'all' ? '全部' : LEVEL_STYLE[level]?.label || level}
              {level !== 'all' && (
                <span style={{
                  ...styles.filterCount,
                  color: LEVEL_STYLE[level]?.color,
                }}>
                  {logs.filter(l => l.level === level).length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div style={styles.logContainer} ref={listRef}>
        {filtered.length === 0 ? (
          <div style={styles.empty}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>
              暂无日志记录
            </div>
          </div>
        ) : (
          filtered.map((entry, i) => {
            const ls = LEVEL_STYLE[entry.level] || LEVEL_STYLE.debug;
            return (
              <div key={i} style={{ ...styles.logEntry, borderLeftColor: ls.color }}>
                <div style={styles.logHeader}>
                  <span style={{
                    ...styles.levelBadge,
                    color: ls.color,
                    background: ls.bg,
                  }}>
                    {ls.label}
                  </span>
                  <span style={styles.logTime}>
                    {new Date(entry.time).toLocaleString('zh-CN', {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                      hour12: false,
                    })}
                  </span>
                </div>
                <div style={styles.logMessage}>{entry.message}</div>
                {entry.details && (
                  <div style={styles.logDetails}>{JSON.stringify(entry.details, null, 2)}</div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

const styles = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
    flexWrap: 'wrap',
    gap: 16,
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
  filterBar: {
    display: 'flex',
    gap: 4,
    background: 'var(--bg-card)',
    borderRadius: 8,
    padding: 3,
    border: '1px solid var(--border)',
  },
  filterBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '6px 12px',
    border: 'none',
    borderRadius: 6,
    background: 'transparent',
    color: 'var(--text-secondary)',
    fontSize: 12,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  filterBtnActive: {
    background: 'var(--bg-input)',
    color: 'var(--text-primary)',
  },
  filterCount: {
    fontSize: 11,
    fontWeight: 700,
  },
  logContainer: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    paddingBottom: 20,
  },
  logEntry: {
    background: 'var(--bg-card)',
    borderRadius: 8,
    padding: '12px 14px',
    borderLeft: '3px solid var(--border)',
    transition: 'background 0.1s',
  },
  logHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  levelBadge: {
    fontSize: 10,
    fontWeight: 700,
    padding: '2px 8px',
    borderRadius: 4,
    letterSpacing: '0.05em',
  },
  logTime: {
    fontSize: 11,
    color: 'var(--text-muted)',
    fontFamily: 'monospace',
  },
  logMessage: {
    fontSize: 13,
    color: 'var(--text-primary)',
    lineHeight: 1.5,
    wordBreak: 'break-word',
  },
  logDetails: {
    marginTop: 8,
    padding: '8px 10px',
    background: 'var(--bg-input)',
    borderRadius: 6,
    fontSize: 11,
    fontFamily: 'monospace',
    color: 'var(--text-secondary)',
    whiteSpace: 'pre-wrap',
    maxHeight: 120,
    overflow: 'auto',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 60,
    opacity: 0.6,
  },
};
