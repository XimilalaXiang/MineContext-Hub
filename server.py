#!/usr/bin/env python3
"""
Context Hub — a lightweight data ingest & management service
for bridging MineContext (Windows desktop) with cloud AI agents.
"""

import os
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")
DB_PATH = Path(os.environ.get("DB_PATH", "/data/context.db"))
SETTINGS_PATH = Path(os.environ.get("SETTINGS_PATH", "/data/settings.json"))

ALL_TYPES = [
    "screenshot", "vault", "todo", "activity", "tip",
    "message", "conversation", "monitoring", "entity",
    "knowledge", "custom",
]

app = FastAPI(title="Context Hub", version="0.1.0")
_start_time = time.time()


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contexts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT    NOT NULL,
            title       TEXT,
            content     TEXT    NOT NULL,
            source      TEXT    DEFAULT 'unknown',
            context_type TEXT,
            tags        TEXT,
            metadata    TEXT,
            confidence  INTEGER,
            importance  INTEGER,
            client_ts   TEXT,
            created_at  TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ctx_type ON contexts(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ctx_created ON contexts(created_at)")
    conn.commit()
    conn.close()


def _load_settings() -> dict:
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text())
    defaults = {t: True for t in ALL_TYPES}
    _save_settings(defaults)
    return defaults


def _save_settings(settings: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def _verify_token(authorization: Optional[str] = Header(None)):
    if not AUTH_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    if authorization[7:] != AUTH_TOKEN:
        raise HTTPException(403, "Invalid token")


# --- Pydantic models ---

class IngestItem(BaseModel):
    type: str
    content: str
    title: Optional[str] = None
    source: Optional[str] = "unknown"
    context_type: Optional[str] = None
    tags: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    confidence: Optional[int] = None
    importance: Optional[int] = None
    client_timestamp: Optional[str] = None


class IngestResponse(BaseModel):
    id: int
    status: str = "ok"


class BatchIngestResponse(BaseModel):
    inserted: int
    skipped: int
    ids: List[int]


class SettingsUpdate(BaseModel):
    settings: Dict[str, bool]


# --- Startup ---

@app.on_event("startup")
def on_startup():
    _init_db()


# --- API ---

@app.post("/ingest", response_model=IngestResponse)
def ingest(item: IngestItem, _=Depends(_verify_token)):
    settings = _load_settings()
    if not settings.get(item.type, True):
        raise HTTPException(422, f"Type '{item.type}' is currently disabled")

    conn = _get_db()
    cur = conn.execute(
        """INSERT INTO contexts
           (type, title, content, source, context_type, tags, metadata,
            confidence, importance, client_ts)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            item.type, item.title, item.content, item.source,
            item.context_type, item.tags,
            json.dumps(item.metadata) if item.metadata else None,
            item.confidence, item.importance, item.client_timestamp,
        ),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return IngestResponse(id=rid)


@app.post("/ingest/batch", response_model=BatchIngestResponse)
def ingest_batch(items: List[IngestItem], _=Depends(_verify_token)):
    settings = _load_settings()
    conn = _get_db()
    ids, skipped = [], 0
    for item in items:
        if not settings.get(item.type, True):
            skipped += 1
            continue
        cur = conn.execute(
            """INSERT INTO contexts
               (type, title, content, source, context_type, tags, metadata,
                confidence, importance, client_ts)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                item.type, item.title, item.content, item.source,
                item.context_type, item.tags,
                json.dumps(item.metadata) if item.metadata else None,
                item.confidence, item.importance, item.client_timestamp,
            ),
        )
        ids.append(cur.lastrowid)
    conn.commit()
    conn.close()
    return BatchIngestResponse(inserted=len(ids), skipped=skipped, ids=ids)


@app.get("/health")
def health():
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - _start_time),
        "db_size_bytes": db_size,
    }


@app.get("/stats")
def stats(_=Depends(_verify_token)):
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM contexts").fetchone()[0]
    by_type = {}
    for row in conn.execute("SELECT type, COUNT(*) as cnt FROM contexts GROUP BY type"):
        by_type[row["type"]] = row["cnt"]
    last = conn.execute(
        "SELECT created_at FROM contexts ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return {
        "total_records": total,
        "by_type": by_type,
        "last_ingested": last["created_at"] if last else None,
        "db_size_mb": round(DB_PATH.stat().st_size / 1048576, 2) if DB_PATH.exists() else 0,
    }


@app.get("/api/contexts")
def list_contexts(
    type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    _=Depends(_verify_token),
):
    conn = _get_db()
    q = "SELECT * FROM contexts"
    params: list = []
    if type:
        q += " WHERE type = ?"
        params.append(type)
    q += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    total_q = "SELECT COUNT(*) FROM contexts"
    if type:
        total_q += " WHERE type = ?"
        total = conn.execute(total_q, [type]).fetchone()[0]
    else:
        total = conn.execute(total_q).fetchone()[0]
    conn.close()
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@app.get("/api/settings")
def get_settings(_=Depends(_verify_token)):
    return _load_settings()


@app.post("/api/settings")
def update_settings(body: SettingsUpdate, _=Depends(_verify_token)):
    current = _load_settings()
    current.update(body.settings)
    _save_settings(current)
    return {"status": "ok", "settings": current}


@app.delete("/api/contexts/{ctx_id}")
def delete_context(ctx_id: int, _=Depends(_verify_token)):
    conn = _get_db()
    conn.execute("DELETE FROM contexts WHERE id = ?", (ctx_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# --- Web UI ---

@app.get("/", response_class=HTMLResponse)
def web_ui():
    return _generate_html()


def _generate_html() -> str:
    return """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Context Hub</title>
<style>
:root{--bg:#0f172a;--card:#1e293b;--text:#e2e8f0;--muted:#94a3b8;--accent:#3b82f6;--green:#22c55e;--red:#ef4444;--border:#334155}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);padding:20px;max-width:1200px;margin:auto}
h1{font-size:1.5rem;margin-bottom:20px;display:flex;align-items:center;gap:10px}
h1 span{font-size:.8rem;color:var(--muted);font-weight:normal}
.header-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:10px}
.lang-switch{display:flex;gap:4px;background:var(--card);border-radius:8px;padding:3px;border:1px solid var(--border)}
.lang-switch button{background:transparent;color:var(--muted);border:none;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:.8rem;transition:.2s}
.lang-switch button.active{background:var(--accent);color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-bottom:24px}
.stat-card{background:var(--card);border-radius:10px;padding:16px;border:1px solid var(--border)}
.stat-card .label{color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}
.stat-card .value{font-size:1.5rem;font-weight:700;margin-top:4px}
.section{background:var(--card);border-radius:10px;padding:20px;margin-bottom:20px;border:1px solid var(--border)}
.section h2{font-size:1.1rem;margin-bottom:14px}
.toggle-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}
.toggle-item{display:flex;align-items:center;justify-content:space-between;background:var(--bg);padding:8px 12px;border-radius:6px;font-size:.85rem}
.switch{position:relative;width:40px;height:22px;cursor:pointer}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;inset:0;background:var(--border);border-radius:22px;transition:.2s}
.slider:before{content:'';position:absolute;height:16px;width:16px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.2s}
input:checked+.slider{background:var(--green)}
input:checked+.slider:before{transform:translateX(18px)}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase}
td{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600;background:var(--accent);color:#fff}
.pagination{display:flex;gap:8px;margin-top:12px;align-items:center;justify-content:center}
.pagination button{background:var(--card);color:var(--text);border:1px solid var(--border);padding:6px 14px;border-radius:6px;cursor:pointer}
.pagination button:disabled{opacity:.4;cursor:default}
.pagination span{color:var(--muted);font-size:.85rem}
.filter-bar{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.filter-bar select,.filter-bar input{background:var(--bg);color:var(--text);border:1px solid var(--border);padding:6px 10px;border-radius:6px;font-size:.85rem}
.empty{text-align:center;color:var(--muted);padding:40px}
#login-screen{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;gap:16px}
#login-screen h1{font-size:1.8rem}
#login-screen .login-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:32px;width:100%;max-width:400px;display:flex;flex-direction:column;gap:14px}
#login-screen input{background:var(--bg);color:var(--text);border:1px solid var(--border);padding:10px 14px;border-radius:8px;font-size:.9rem;width:100%}
#login-screen button{background:var(--accent);color:#fff;border:none;padding:10px;border-radius:8px;font-size:.9rem;cursor:pointer;font-weight:600;transition:.2s}
#login-screen button:hover{opacity:.9}
#login-screen .error{color:var(--red);font-size:.85rem;text-align:center;display:none}
#main-app{display:none}
.logout-btn{background:transparent;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:6px;cursor:pointer;font-size:.8rem;transition:.2s}
.logout-btn:hover{color:var(--red);border-color:var(--red)}
</style>
</head>
<body>

<div id="login-screen">
  <h1>Context Hub</h1>
  <div class="login-box">
    <div class="lang-switch" style="align-self:center;margin-bottom:8px">
      <button onclick="setLang('zh')" id="login-btn-zh">中文</button>
      <button onclick="setLang('en')" id="login-btn-en">EN</button>
    </div>
    <input type="password" id="token-input" onkeydown="if(event.key==='Enter')doLogin()">
    <button onclick="doLogin()" id="login-submit"></button>
    <div class="error" id="login-error"></div>
  </div>
</div>

<div id="main-app">
  <div class="header-row">
    <h1>Context Hub <span>v0.1.0</span></h1>
    <div style="display:flex;gap:8px;align-items:center">
      <div class="lang-switch" id="lang-switch">
        <button onclick="setLang('zh')" id="btn-zh">中文</button>
        <button onclick="setLang('en')" id="btn-en">EN</button>
      </div>
      <button class="logout-btn" onclick="doLogout()" id="logout-btn"></button>
    </div>
  </div>

  <div class="grid" id="stats-grid"></div>

  <div class="section">
    <h2 id="h-settings"></h2>
    <div class="toggle-grid" id="toggles"></div>
  </div>

  <div class="section">
    <h2 id="h-recent"></h2>
    <div class="filter-bar">
      <select id="filter-type" onchange="loadData()"></select>
    </div>
    <div id="data-table"></div>
    <div class="pagination" id="pagination"></div>
  </div>
</div>

<script>
let TOKEN = localStorage.getItem('ctx-hub-token') || new URLSearchParams(location.search).get('token') || '';
let H = TOKEN ? {'Authorization':'Bearer '+TOKEN} : {};
let page = 0, pageSize = 20, totalRecords = 0;
let authed = false;

const I18N = {
  zh: {
    settings: '数据采集设置',
    recent: '最近数据',
    allTypes: '全部类型',
    totalRecords: '总记录数',
    dbSize: '数据库大小',
    lastIngested: '最近写入',
    never: '暂无',
    login: '登录',
    tokenPlaceholder: '请输入访问令牌...',
    loginBtn: '登录',
    loginError: '令牌无效',
    logout: '退出登录',
    noData: '暂无数据',
    prev: '上一页',
    next: '下一页',
    page: '第',
    of: '页 / 共',
    pages: '页',
    total: '条',
    thId: 'ID',
    thType: '类型',
    thTitle: '标题',
    thContent: '内容',
    thSource: '来源',
    thTime: '时间',
    typeNames: {
      screenshot: '截图', vault: '知识库', todo: '待办',
      activity: '活动', tip: '提示', message: '消息',
      conversation: '对话', monitoring: '监控', entity: '实体',
      knowledge: '知识', custom: '自定义'
    }
  },
  en: {
    settings: 'Data Collection Settings',
    recent: 'Recent Data',
    allTypes: 'All types',
    totalRecords: 'Total Records',
    dbSize: 'DB Size',
    lastIngested: 'Last Ingested',
    never: 'Never',
    noData: 'No data yet',
    prev: 'Prev',
    next: 'Next',
    page: 'Page ',
    of: ' / ',
    pages: '',
    total: ' total',
    thId: 'ID',
    thType: 'Type',
    thTitle: 'Title',
    thContent: 'Content',
    thSource: 'Source',
    thTime: 'Time',
    typeNames: {},
    login: 'Login',
    tokenPlaceholder: 'Enter access token...',
    loginBtn: 'Login',
    loginError: 'Invalid token',
    logout: 'Logout'
  }
};

let lang = localStorage.getItem('ctx-hub-lang') || 'zh';
const t = () => I18N[lang];
const typeName = (k) => t().typeNames[k] || k;

function setLang(l) {
  lang = l;
  localStorage.setItem('ctx-hub-lang', l);
  ['btn-zh','login-btn-zh'].forEach(id=>{const e=document.getElementById(id);if(e)e.className=l==='zh'?'active':'';});
  ['btn-en','login-btn-en'].forEach(id=>{const e=document.getElementById(id);if(e)e.className=l==='en'?'active':'';});
  document.documentElement.lang = l;
  applyLoginLang();
  if(authed) applyLang();
}

function applyLoginLang() {
  const ti = document.getElementById('token-input');
  if(ti) ti.placeholder = t().tokenPlaceholder;
  const ls = document.getElementById('login-submit');
  if(ls) ls.textContent = t().loginBtn;
  const le = document.getElementById('login-error');
  if(le) le.textContent = t().loginError;
  const lo = document.getElementById('logout-btn');
  if(lo) lo.textContent = t().logout;
}

function applyLang() {
  const hs = document.getElementById('h-settings');
  if(hs) hs.textContent = t().settings;
  const hr = document.getElementById('h-recent');
  if(hr) hr.textContent = t().recent;
  applyLoginLang();
  loadStats(); loadSettings(); loadData();
}

async function doLogin() {
  const input = document.getElementById('token-input').value.trim();
  if(!input) return;
  TOKEN = input;
  H = {'Authorization':'Bearer '+TOKEN};
  try {
    const r = await fetch('/stats', {headers: H});
    if(r.ok) {
      localStorage.setItem('ctx-hub-token', TOKEN);
      authed = true;
      document.getElementById('login-screen').style.display = 'none';
      document.getElementById('main-app').style.display = 'block';
      applyLang();
    } else {
      document.getElementById('login-error').style.display = 'block';
    }
  } catch(e) {
    document.getElementById('login-error').style.display = 'block';
  }
}

function doLogout() {
  TOKEN = '';
  H = {};
  authed = false;
  localStorage.removeItem('ctx-hub-token');
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('main-app').style.display = 'none';
  document.getElementById('token-input').value = '';
  document.getElementById('login-error').style.display = 'none';
}

async function api(path, opts={}){
  const r = await fetch(path, {...opts, headers:{...H,'Content-Type':'application/json',...(opts.headers||{})}});
  return r.json();
}

async function loadStats(){
  const s = await api('/stats');
  const g = document.getElementById('stats-grid');
  const cards = [
    {label:t().totalRecords, value:s.total_records},
    {label:t().dbSize, value:s.db_size_mb+' MB'},
    {label:t().lastIngested, value:s.last_ingested||t().never},
  ];
  Object.entries(s.by_type||{}).forEach(([k,v])=>cards.push({label:typeName(k), value:v}));
  g.innerHTML = cards.map(c=>`<div class="stat-card"><div class="label">${c.label}</div><div class="value">${c.value}</div></div>`).join('');
}

async function loadSettings(){
  const s = await api('/api/settings');
  const g = document.getElementById('toggles');
  g.innerHTML = Object.entries(s).map(([k,v])=>`
    <div class="toggle-item">
      <span>${typeName(k)}</span>
      <label class="switch"><input type="checkbox" ${v?'checked':''} onchange="toggleType('${k}',this.checked)"><span class="slider"></span></label>
    </div>`).join('');
  const sel = document.getElementById('filter-type');
  const curVal = sel.value;
  sel.innerHTML = `<option value="">${t().allTypes}</option>`;
  Object.keys(s).forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent=typeName(k);sel.appendChild(o);});
  sel.value = curVal;
}

async function toggleType(type, enabled){
  await api('/api/settings',{method:'POST',body:JSON.stringify({settings:{[type]:enabled}})});
}

async function loadData(){
  const type = document.getElementById('filter-type').value;
  const d = await api(`/api/contexts?limit=${pageSize}&offset=${page*pageSize}${type?'&type='+type:''}`);
  totalRecords = d.total;
  const el = document.getElementById('data-table');
  if(!d.items.length){el.innerHTML=`<div class="empty">${t().noData}</div>`;document.getElementById('pagination').innerHTML='';return;}
  el.innerHTML=`<table><thead><tr><th>${t().thId}</th><th>${t().thType}</th><th>${t().thTitle}</th><th>${t().thContent}</th><th>${t().thSource}</th><th>${t().thTime}</th></tr></thead><tbody>${
    d.items.map(r=>`<tr><td>${r.id}</td><td><span class="badge">${typeName(r.type)}</span></td><td>${r.title||'-'}</td><td>${(r.content||'').substring(0,80)}</td><td>${r.source||'-'}</td><td>${r.created_at||'-'}</td></tr>`).join('')
  }</tbody></table>`;
  const pages = Math.ceil(totalRecords/pageSize);
  document.getElementById('pagination').innerHTML=`
    <button onclick="page=Math.max(0,page-1);loadData()" ${page<=0?'disabled':''}>${t().prev}</button>
    <span>${t().page}${page+1}${t().of}${pages}${t().pages} (${totalRecords}${t().total})</span>
    <button onclick="page++;loadData()" ${page>=pages-1?'disabled':''}>${t().next}</button>`;
}

setLang(lang);

(async function init() {
  if(TOKEN) {
    try {
      const r = await fetch('/stats', {headers: H});
      if(r.ok) {
        authed = true;
        document.getElementById('login-screen').style.display = 'none';
        document.getElementById('main-app').style.display = 'block';
        applyLang();
        setInterval(loadStats, 30000);
        return;
      }
    } catch(e) {}
    localStorage.removeItem('ctx-hub-token');
    TOKEN = '';
    H = {};
  }
  applyLoginLang();
})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
