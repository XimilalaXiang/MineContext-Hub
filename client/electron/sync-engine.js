const { EventEmitter } = require('events');
const path = require('path');
const fs = require('fs');
const os = require('os');
const https = require('https');
const http = require('http');

const TABLE_DEFS = {
  vaults: {
    type: 'vault',
    id_col: 'id',
    time_col: 'created_at',
    fields: ['id', 'title', 'summary', 'content', 'tags', 'document_type', 'created_at', 'updated_at'],
    content_field: 'content',
    title_field: 'title',
  },
  todo: {
    type: 'todo',
    id_col: 'id',
    time_col: 'created_at',
    fields: ['id', 'content', 'created_at', 'start_time', 'end_time', 'status', 'urgency', 'assignee', 'reason'],
    content_field: 'content',
    title_field: null,
  },
  activity: {
    type: 'activity',
    id_col: 'id',
    time_col: 'start_time',
    fields: ['id', 'title', 'content', 'resources', 'metadata', 'start_time', 'end_time'],
    content_field: 'content',
    title_field: 'title',
  },
  tips: {
    type: 'tip',
    id_col: 'id',
    time_col: 'created_at',
    fields: ['id', 'content', 'created_at'],
    content_field: 'content',
    title_field: null,
  },
  conversations: {
    type: 'conversation',
    id_col: 'id',
    time_col: 'created_at',
    fields: ['id', 'title', 'user_id', 'page_name', 'status', 'metadata', 'created_at', 'updated_at'],
    content_field: 'title',
    title_field: 'title',
  },
  messages: {
    type: 'message',
    id_col: 'id',
    time_col: 'created_at',
    fields: ['id', 'conversation_id', 'role', 'content', 'status', 'token_count', 'created_at'],
    content_field: 'content',
    title_field: null,
  },
  monitoring_data_stats: {
    type: 'monitoring',
    id_col: 'id',
    time_col: 'created_at',
    fields: ['id', 'time_bucket', 'data_type', 'count', 'context_type', 'metadata', 'created_at'],
    content_field: 'data_type',
    title_field: 'data_type',
  },
};

class SyncEngine extends EventEmitter {
  constructor(store) {
    super();
    this.store = store;
    this.state = {};
    this.running = false;
    this.timer = null;
    this.logs = [];
    this.maxLogs = 500;
    this.stats = {
      totalSynced: 0,
      lastSyncTime: null,
      lastSyncResult: null,
      syncCount: 0,
      errorCount: 0,
      byType: {},
    };
    this.statusInfo = {
      status: 'stopped',
      message: '',
    };
    this._loadState();
  }

  _loadState() {
    try {
      const stateData = this.store.get('sync_state');
      if (stateData && typeof stateData === 'object') {
        this.state = stateData;
      }
    } catch {
      this.state = {};
    }
  }

  _saveState() {
    this.store.set('sync_state', this.state);
  }

  _addLog(level, message, details = null) {
    const entry = {
      time: new Date().toISOString(),
      level,
      message,
      details,
    };
    this.logs.unshift(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(0, this.maxLogs);
    }
    this.emit('log', entry);
  }

  _setStatus(status, message = '') {
    this.statusInfo = { status, message };
    this.emit('status', this.statusInfo);
  }

  start() {
    if (this.running) return;
    const token = this.store.get('hub_token');
    if (!token) {
      this._addLog('warn', '未配置 Hub Token，无法启动同步');
      this._setStatus('error', '未配置 Token');
      return;
    }

    this.running = true;
    this._setStatus('running', '同步服务已启动');
    this._addLog('info', '同步服务已启动');

    this.syncOnce();
    const interval = (this.store.get('sync_interval_seconds') || 60) * 1000;
    this.timer = setInterval(() => this.syncOnce(), interval);
  }

  stop() {
    if (!this.running) return;
    this.running = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this._setStatus('stopped', '同步服务已停止');
    this._addLog('info', '同步服务已停止');
  }

  restart() {
    this.stop();
    setTimeout(() => this.start(), 500);
  }

  getStatus() {
    return this.statusInfo;
  }

  getLogs() {
    return this.logs;
  }

  getStats() {
    return this.stats;
  }

  _findMineContextDB() {
    const explicit = this.store.get('db_path');
    if (explicit && fs.existsSync(explicit)) {
      return explicit;
    }
    if (explicit) {
      this._addLog('warn', `配置的数据库路径不存在: ${explicit}`);
    }

    const envDirs = [
      process.env.APPDATA,
      process.env.LOCALAPPDATA,
      process.env.USERPROFILE,
    ].filter(Boolean);

    const candidates = [];
    for (const base of envDirs) {
      candidates.push(
        path.join(base, 'MineContext', 'persist', 'sqlite', 'app.db'),
        path.join(base, 'minecontext', 'persist', 'sqlite', 'app.db'),
        path.join(base, '.minecontext', 'persist', 'sqlite', 'app.db'),
        path.join(base, 'MineContext', 'app.db'),
      );
    }

    for (const c of candidates) {
      if (fs.existsSync(c)) {
        this._addLog('info', `找到 MineContext 数据库: ${c}`);
        return c;
      }
    }

    return null;
  }

  async syncOnce() {
    if (!this.running && this.statusInfo.status !== 'stopped') return;

    this._setStatus('syncing', '正在同步...');

    try {
      const dbPath = this._findMineContextDB();
      if (!dbPath) {
        this._addLog('error', '未找到 MineContext 数据库，请在设置中手动指定路径');
        this._setStatus('error', '未找到数据库');
        return;
      }

      const tmpPath = path.join(path.dirname(dbPath), '.sync_copy_app.db');
      fs.copyFileSync(dbPath, tmpPath);

      let Database;
      try {
        Database = require('better-sqlite3');
      } catch {
        this._addLog('error', 'better-sqlite3 模块加载失败，使用 HTTP 模式');
        this._setStatus('error', 'SQLite 模块不可用');
        this._cleanupTmp(tmpPath);
        return;
      }

      const db = new Database(tmpPath, { readonly: true });
      const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(r => r.name);

      const enabledTypes = new Set(this.store.get('sync_types') || Object.keys(TABLE_DEFS));
      const hubUrl = this.store.get('hub_url');
      const token = this.store.get('hub_token');
      const batchSize = this.store.get('batch_size') || 100;
      let totalPushed = 0;

      for (const [tableName, tdef] of Object.entries(TABLE_DEFS)) {
        if (!tables.includes(tableName)) continue;
        if (!enabledTypes.has(tableName)) continue;

        const lastId = this.state[`last_id_${tableName}`] || 0;

        const availableCols = db.pragma(`table_info(${tableName})`).map(c => c.name);
        const cols = tdef.fields.filter(f => availableCols.includes(f));

        const sql = `SELECT ${cols.join(', ')} FROM ${tableName} WHERE ${tdef.id_col} > ? ORDER BY ${tdef.id_col} ASC LIMIT 500`;
        const rows = db.prepare(sql).all(lastId);

        if (!rows.length) continue;

        this._addLog('info', `[${tableName}] 发现 ${rows.length} 条新数据 (last_id=${lastId})`);

        const payloads = rows.map(row => this._rowToPayload(row, tdef, tableName));

        for (let i = 0; i < payloads.length; i += batchSize) {
          const batch = payloads.slice(i, i + batchSize);
          const success = await this._pushBatch(hubUrl, token, batch);
          if (success) {
            const maxId = rows[Math.min(i + batchSize, rows.length) - 1][tdef.id_col];
            this.state[`last_id_${tableName}`] = maxId;
            this._saveState();
            totalPushed += batch.length;

            this.stats.byType[tdef.type] = (this.stats.byType[tdef.type] || 0) + batch.length;
          } else {
            this._addLog('warn', `[${tableName}] 批次推送失败，下次重试`);
            break;
          }
        }
      }

      db.close();
      this._cleanupTmp(tmpPath);

      this.stats.totalSynced += totalPushed;
      this.stats.lastSyncTime = new Date().toISOString();
      this.stats.syncCount++;

      if (totalPushed > 0) {
        this._addLog('info', `本轮同步完成: 共推送 ${totalPushed} 条数据`);
        this.stats.lastSyncResult = 'success';
      } else {
        this._addLog('debug', '本轮无新数据');
        this.stats.lastSyncResult = 'no_data';
      }

      this._setStatus('running', `上次同步: ${new Date().toLocaleTimeString()}`);
      this.emit('stats', this.stats);
    } catch (err) {
      this._addLog('error', `同步异常: ${err.message}`);
      this.stats.errorCount++;
      this.stats.lastSyncResult = 'error';
      this._setStatus('error', err.message);
      this.emit('stats', this.stats);
    }
  }

  _rowToPayload(row, tdef, tableName) {
    const contentVal = row[tdef.content_field] || '';
    const titleVal = tdef.title_field ? row[tdef.title_field] : null;
    const timeVal = row[tdef.time_col] || '';

    const meta = {};
    for (const [k, v] of Object.entries(row)) {
      if (['content', 'title', 'summary'].includes(k)) continue;
      if (v != null) meta[k] = v;
    }

    return {
      type: tdef.type,
      content: String(contentVal),
      title: titleVal ? String(titleVal) : null,
      source: `minecontext/${tableName}`,
      context_type: tdef.type,
      tags: row.tags || null,
      metadata: Object.keys(meta).length ? meta : null,
      client_timestamp: timeVal ? String(timeVal) : null,
    };
  }

  _pushBatch(hubUrl, token, payloads) {
    return new Promise((resolve) => {
      const url = new URL(`${hubUrl.replace(/\/+$/, '')}/ingest/batch`);
      const isHttps = url.protocol === 'https:';
      const lib = isHttps ? https : http;

      const body = JSON.stringify(payloads);
      const options = {
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname,
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
        },
        timeout: 30000,
      };

      const req = lib.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          if (res.statusCode === 200) {
            try {
              const json = JSON.parse(data);
              this._addLog('info', `推送成功: inserted=${json.inserted}, skipped=${json.skipped}`);
            } catch { /* ignore parse error */ }
            resolve(true);
          } else if (res.statusCode === 422) {
            this._addLog('warn', `部分数据类型被禁用: ${data}`);
            resolve(true);
          } else {
            this._addLog('error', `推送失败 HTTP ${res.statusCode}: ${data}`);
            resolve(false);
          }
        });
      });

      req.on('error', (err) => {
        this._addLog('error', `网络错误: ${err.message}`);
        resolve(false);
      });

      req.on('timeout', () => {
        req.destroy();
        this._addLog('error', '推送超时');
        resolve(false);
      });

      req.write(body);
      req.end();
    });
  }

  _cleanupTmp(tmpPath) {
    try {
      if (fs.existsSync(tmpPath)) fs.unlinkSync(tmpPath);
    } catch { /* ignore */ }
  }
}

module.exports = { SyncEngine, TABLE_DEFS };
