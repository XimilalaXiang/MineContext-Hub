import React, { useState, useEffect } from 'react';

const SYNC_TYPE_OPTIONS = [
  { key: 'vaults', label: '知识库 (vaults)', desc: 'MineContext 知识库文档' },
  { key: 'todo', label: '待办 (todo)', desc: '待办事项列表' },
  { key: 'activity', label: '活动 (activity)', desc: '用户活动记录' },
  { key: 'tips', label: '提示 (tips)', desc: '智能提示数据' },
  { key: 'conversations', label: '对话 (conversations)', desc: 'AI 对话记录' },
  { key: 'messages', label: '消息 (messages)', desc: '对话消息内容' },
  { key: 'monitoring_data_stats', label: '监控 (monitoring)', desc: '系统监控统计' },
];

export default function Settings({ config, updateConfig, updateConfigAll, api }) {
  const [form, setForm] = useState({
    hub_url: '',
    hub_token: '',
    db_path: '',
    sync_interval_seconds: 60,
    batch_size: 100,
    sync_types: [],
    minimize_to_tray: true,
  });
  const [saved, setSaved] = useState(false);
  const [autoStart, setAutoStart] = useState(false);

  useEffect(() => {
    if (config) {
      setForm({
        hub_url: config.hub_url || '',
        hub_token: config.hub_token || '',
        db_path: config.db_path || '',
        sync_interval_seconds: config.sync_interval_seconds || 60,
        batch_size: config.batch_size || 100,
        sync_types: config.sync_types || [],
        minimize_to_tray: config.minimize_to_tray !== false,
      });
    }
    api.autostart.get().then(setAutoStart);
  }, [config, api]);

  const handleSave = async () => {
    await updateConfigAll(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleSelectDB = async () => {
    const file = await api.app.selectFile();
    if (file) {
      setForm(prev => ({ ...prev, db_path: file }));
    }
  };

  const toggleSyncType = (key) => {
    setForm(prev => {
      const types = new Set(prev.sync_types);
      if (types.has(key)) types.delete(key);
      else types.add(key);
      return { ...prev, sync_types: [...types] };
    });
  };

  const handleAutoStart = async (e) => {
    const enable = e.target.checked;
    await api.autostart.set(enable);
    setAutoStart(enable);
  };

  return (
    <div>
      <div style={styles.header}>
        <div>
          <h1 style={styles.pageTitle}>设置</h1>
          <p style={styles.pageDesc}>配置同步连接和应用行为</p>
        </div>
        <button
          onClick={handleSave}
          style={{
            ...styles.saveBtn,
            background: saved ? 'var(--green)' : 'var(--accent)',
          }}
          onMouseEnter={e => { if (!saved) e.currentTarget.style.background = 'var(--accent-hover)'; }}
          onMouseLeave={e => { if (!saved) e.currentTarget.style.background = 'var(--accent)'; }}
        >
          {saved ? (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              已保存
            </>
          ) : '保存设置'}
        </button>
      </div>

      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
            <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
          </svg>
          连接配置
        </h2>

        <div style={styles.fieldGroup}>
          <label style={styles.label}>Hub 地址</label>
          <input
            style={styles.input}
            type="text"
            value={form.hub_url}
            onChange={e => setForm(prev => ({ ...prev, hub_url: e.target.value }))}
            placeholder="https://context.ximilala.com"
          />
        </div>

        <div style={styles.fieldGroup}>
          <label style={styles.label}>Hub Token</label>
          <input
            style={styles.input}
            type="password"
            value={form.hub_token}
            onChange={e => setForm(prev => ({ ...prev, hub_token: e.target.value }))}
            placeholder="输入访问令牌"
          />
        </div>

        <div style={styles.fieldGroup}>
          <label style={styles.label}>数据库路径 <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>（留空自动检测）</span></label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              style={{ ...styles.input, flex: 1 }}
              type="text"
              value={form.db_path}
              onChange={e => setForm(prev => ({ ...prev, db_path: e.target.value }))}
              placeholder="自动检测 MineContext 数据库"
            />
            <button
              onClick={handleSelectDB}
              style={styles.browseBtn}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover)'}
              onMouseLeave={e => e.currentTarget.style.background = 'var(--bg-card)'}
            >
              浏览...
            </button>
          </div>
        </div>
      </div>

      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          同步参数
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div style={styles.fieldGroup}>
            <label style={styles.label}>同步间隔（秒）</label>
            <input
              style={styles.input}
              type="number"
              min="10"
              max="3600"
              value={form.sync_interval_seconds}
              onChange={e => setForm(prev => ({ ...prev, sync_interval_seconds: parseInt(e.target.value) || 60 }))}
            />
          </div>
          <div style={styles.fieldGroup}>
            <label style={styles.label}>每批推送条数</label>
            <input
              style={styles.input}
              type="number"
              min="10"
              max="500"
              value={form.batch_size}
              onChange={e => setForm(prev => ({ ...prev, batch_size: parseInt(e.target.value) || 100 }))}
            />
          </div>
        </div>
      </div>

      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12l2 2 4-4"/>
          </svg>
          同步数据类型
        </h2>
        <div style={styles.typeGrid}>
          {SYNC_TYPE_OPTIONS.map(opt => {
            const checked = form.sync_types.includes(opt.key);
            return (
              <label key={opt.key} style={styles.typeItem}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    onClick={() => toggleSyncType(opt.key)}
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: 4,
                      border: `2px solid ${checked ? 'var(--accent)' : 'var(--border)'}`,
                      background: checked ? 'var(--accent)' : 'transparent',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                      flexShrink: 0,
                    }}
                  >
                    {checked && (
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    )}
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{opt.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{opt.desc}</div>
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--yellow)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
          应用设置
        </h2>

        <div style={styles.toggleRow}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>关闭时最小化到托盘</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>关闭窗口后程序继续在后台运行</div>
          </div>
          <label style={styles.switch}>
            <input
              type="checkbox"
              checked={form.minimize_to_tray}
              onChange={e => setForm(prev => ({ ...prev, minimize_to_tray: e.target.checked }))}
            />
            <span style={styles.slider} />
          </label>
        </div>

        <div style={{ ...styles.toggleRow, borderTop: '1px solid var(--border)', paddingTop: 14, marginTop: 14 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>开机自动启动</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>登录 Windows 时自动运行</div>
          </div>
          <label style={styles.switch}>
            <input type="checkbox" checked={autoStart} onChange={handleAutoStart} />
            <span style={styles.slider} />
          </label>
        </div>
      </div>
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
  saveBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 20px',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
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
    marginBottom: 16,
    color: 'var(--text-primary)',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  fieldGroup: {
    marginBottom: 14,
  },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text-primary)',
    fontSize: 13,
    outline: 'none',
    transition: 'border-color 0.15s',
  },
  browseBtn: {
    padding: '10px 16px',
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text-primary)',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s',
  },
  typeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
    gap: 8,
  },
  typeItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 12px',
    background: 'var(--bg-input)',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  toggleRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 16,
  },
  switch: {
    position: 'relative',
    width: 42,
    height: 24,
    display: 'inline-block',
    cursor: 'pointer',
    flexShrink: 0,
  },
  slider: {
    position: 'absolute',
    inset: 0,
    background: 'var(--border)',
    borderRadius: 24,
    transition: '0.2s',
    pointerEvents: 'none',
  },
};

const styleSheet = document.createElement('style');
styleSheet.textContent = `
  .settings-switch input { opacity: 0; width: 0; height: 0; position: absolute; }
`;
if (!document.querySelector('[data-settings-style]')) {
  styleSheet.setAttribute('data-settings-style', '');
  document.head.appendChild(styleSheet);
}

const toggleStyleSheet = document.createElement('style');
toggleStyleSheet.textContent = `
  label > input[type="checkbox"] { opacity: 0; width: 0; height: 0; position: absolute; }
  label > input[type="checkbox"] + span {
    position: absolute; inset: 0; background: var(--border); border-radius: 24px; transition: 0.2s;
  }
  label > input[type="checkbox"] + span::before {
    content: ''; position: absolute; height: 18px; width: 18px; left: 3px; bottom: 3px;
    background: white; border-radius: 50%; transition: 0.2s;
  }
  label > input[type="checkbox"]:checked + span { background: var(--green); }
  label > input[type="checkbox"]:checked + span::before { transform: translateX(18px); }
`;
if (!document.querySelector('[data-toggle-style]')) {
  toggleStyleSheet.setAttribute('data-toggle-style', '');
  document.head.appendChild(toggleStyleSheet);
}
