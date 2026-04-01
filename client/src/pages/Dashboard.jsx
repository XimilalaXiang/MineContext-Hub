import React from 'react';

const TYPE_LABELS = {
  vault: { name: '知识库', color: '#8b5cf6' },
  todo: { name: '待办', color: '#f59e0b' },
  activity: { name: '活动', color: '#3b82f6' },
  tip: { name: '提示', color: '#06b6d4' },
  conversation: { name: '对话', color: '#10b981' },
  message: { name: '消息', color: '#ec4899' },
  monitoring: { name: '监控', color: '#ef4444' },
};

function StatCard({ label, value, color, icon }) {
  return (
    <div style={styles.card}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {icon && <div style={{ ...styles.iconBox, background: `${color}18` }}>{icon}</div>}
        <div>
          <div style={styles.cardLabel}>{label}</div>
          <div style={{ ...styles.cardValue, color: color || 'var(--text-primary)' }}>{value}</div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard({ syncStatus, syncStats, api }) {
  const handleSync = () => api.sync.once();
  const handleToggle = () => {
    if (syncStatus?.status === 'running' || syncStatus?.status === 'syncing') {
      api.sync.stop();
    } else {
      api.sync.start();
    }
  };

  const isRunning = syncStatus?.status === 'running' || syncStatus?.status === 'syncing';

  return (
    <div>
      <div style={styles.header}>
        <div>
          <h1 style={styles.pageTitle}>仪表盘</h1>
          <p style={styles.pageDesc}>监控同步状态和数据统计</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={handleSync}
            style={styles.btnOutline}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
            </svg>
            立即同步
          </button>
          <button
            onClick={handleToggle}
            style={{
              ...styles.btnPrimary,
              background: isRunning ? 'var(--red)' : 'var(--green)',
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
            onMouseLeave={e => e.currentTarget.style.opacity = '1'}
          >
            {isRunning ? (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
                停止同步
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                启动同步
              </>
            )}
          </button>
        </div>
      </div>

      <div style={styles.grid}>
        <StatCard
          label="同步状态"
          value={{
            running: '运行中',
            syncing: '同步中',
            stopped: '已停止',
            error: '异常',
          }[syncStatus?.status] || '未知'}
          color={{
            running: 'var(--green)',
            syncing: 'var(--accent)',
            stopped: 'var(--text-muted)',
            error: 'var(--red)',
          }[syncStatus?.status]}
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={
              { running: 'var(--green)', syncing: 'var(--accent)', stopped: 'var(--text-muted)', error: 'var(--red)' }[syncStatus?.status] || 'var(--text-muted)'
            } strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          }
        />
        <StatCard
          label="累计同步"
          value={`${syncStats?.totalSynced || 0} 条`}
          color="var(--accent)"
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          }
        />
        <StatCard
          label="同步次数"
          value={syncStats?.syncCount || 0}
          color="var(--purple)"
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" strokeWidth="2"><path d="M12 2v20M2 12h20"/></svg>
          }
        />
        <StatCard
          label="错误次数"
          value={syncStats?.errorCount || 0}
          color="var(--red)"
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          }
        />
      </div>

      {syncStatus?.message && (
        <div style={styles.statusMessage}>
          {syncStatus.message}
        </div>
      )}

      {syncStats?.lastSyncTime && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>上次同步</h2>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {new Date(syncStats.lastSyncTime).toLocaleString('zh-CN')}
          </div>
        </div>
      )}

      {syncStats?.byType && Object.keys(syncStats.byType).length > 0 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>各类型同步统计</h2>
          <div style={styles.typeGrid}>
            {Object.entries(syncStats.byType).map(([type, count]) => {
              const info = TYPE_LABELS[type] || { name: type, color: 'var(--text-secondary)' };
              return (
                <div key={type} style={styles.typeCard}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: info.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{info.name}</span>
                  </div>
                  <span style={{ fontSize: 18, fontWeight: 700, color: info.color }}>{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 24,
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
  btnOutline: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 16px',
    border: '1px solid var(--border)',
    borderRadius: 8,
    background: 'transparent',
    color: 'var(--text-primary)',
    fontSize: 13,
    fontWeight: 500,
    transition: 'all 0.15s',
  },
  btnPrimary: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 16px',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 13,
    fontWeight: 600,
    transition: 'all 0.15s',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: 14,
    marginBottom: 24,
  },
  card: {
    background: 'var(--bg-card)',
    borderRadius: 12,
    padding: '18px 16px',
    border: '1px solid var(--border)',
    transition: 'border-color 0.15s',
  },
  cardLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 2,
  },
  cardValue: {
    fontSize: 20,
    fontWeight: 700,
  },
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  statusMessage: {
    padding: '10px 16px',
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    fontSize: 13,
    color: 'var(--text-secondary)',
    marginBottom: 20,
  },
  section: {
    background: 'var(--bg-card)',
    borderRadius: 12,
    padding: 20,
    border: '1px solid var(--border)',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 14,
    color: 'var(--text-primary)',
  },
  typeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: 10,
  },
  typeCard: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 14px',
    background: 'var(--bg-input)',
    borderRadius: 8,
  },
};
