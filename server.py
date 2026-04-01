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


# --- MCP Streamable HTTP ---

MCP_SERVER_INFO = {
    "name": "context-hub",
    "version": "0.1.0",
}
MCP_CAPABILITIES = {
    "tools": {},
}
MCP_TOOLS = [
    {
        "name": "get_user_todos",
        "description": "获取用户当前待办事项。Returns the user's current todo items from MineContext.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["all", "active", "completed"],
                    "description": "Filter by status: all, active (status=0), completed (status=1)",
                    "default": "all",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "get_recent_activities",
        "description": "获取用户最近的电脑操作活动记录。Returns the user's recent desktop activities from MineContext.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Look back N hours (default 24)",
                    "default": 24,
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "get_tips",
        "description": "获取 MineContext 生成的智能提示。Returns AI-generated tips/insights from MineContext.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of results",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "search_context",
        "description": "全文搜索上下文数据（待办、活动、提示）。Full-text search across todo, activity, and tip data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "type": {
                    "type": "string",
                    "enum": ["todo", "activity", "tip", ""],
                    "description": "Optionally filter by data type",
                    "default": "",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
]


def _slim_row(row: dict, row_type: str) -> dict:
    """Extract only essential fields from a database row, parsing metadata intelligently."""
    meta = {}
    if row.get("metadata"):
        try:
            raw = json.loads(row["metadata"])
            if isinstance(raw, dict):
                inner_meta = raw.get("metadata")
                if isinstance(inner_meta, str):
                    try:
                        inner_meta = json.loads(inner_meta)
                    except (json.JSONDecodeError, TypeError):
                        inner_meta = None
                if isinstance(inner_meta, dict):
                    ei = inner_meta.get("extracted_insights", {})
                    if ei.get("key_entities"):
                        meta["key_entities"] = ei["key_entities"]
                    if ei.get("focus_areas"):
                        meta["focus_areas"] = ei["focus_areas"]
                    if inner_meta.get("category_distribution"):
                        meta["category"] = inner_meta["category_distribution"]
                if raw.get("status") is not None:
                    meta["status"] = raw["status"]
                if raw.get("urgency") is not None:
                    meta["urgency"] = raw["urgency"]
                if raw.get("assignee"):
                    meta["assignee"] = raw["assignee"]
                if raw.get("reason"):
                    meta["reason"] = raw["reason"]
                if raw.get("start_time"):
                    meta["start_time"] = raw["start_time"]
                if raw.get("end_time"):
                    meta["end_time"] = raw["end_time"]
        except (json.JSONDecodeError, TypeError):
            pass

    result = {"id": row["id"], "type": row_type}
    if row.get("title"):
        result["title"] = row["title"]
    content = row.get("content") or ""
    if len(content) > 500:
        result["content"] = content[:500] + "..."
    else:
        result["content"] = content
    if row.get("client_ts"):
        result["time"] = row["client_ts"]
    elif row.get("created_at"):
        result["time"] = row["created_at"]
    if meta:
        result["meta"] = meta
    return result


def _mcp_call_tool(name: str, arguments: dict) -> list:
    conn = _get_db()
    try:
        if name == "get_user_todos":
            status_filter = arguments.get("status", "all")
            limit = min(arguments.get("limit", 20), 100)
            q = "SELECT * FROM contexts WHERE type = 'todo'"
            params: list = []
            if status_filter == "active":
                q += " AND (metadata LIKE '%\"status\": 0%' OR metadata LIKE '%\"status\":0%')"
            elif status_filter == "completed":
                q += " AND (metadata LIKE '%\"status\": 1%' OR metadata LIKE '%\"status\":1%')"
            q += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            rows = [_slim_row(dict(r), "todo") for r in conn.execute(q, params).fetchall()]
            text = json.dumps(rows, ensure_ascii=False, indent=2) if rows else "No todo items found."
            return [{"type": "text", "text": text}]

        elif name == "get_recent_activities":
            hours = arguments.get("hours", 24)
            limit = min(arguments.get("limit", 20), 100)
            cutoff = f"datetime('now', '-{hours} hours')"
            q = f"SELECT * FROM contexts WHERE type = 'activity' AND (client_ts >= {cutoff} OR client_ts IS NULL) ORDER BY id DESC LIMIT ?"
            rows = [_slim_row(dict(r), "activity") for r in conn.execute(q, [limit]).fetchall()]
            text = json.dumps(rows, ensure_ascii=False, indent=2) if rows else "No recent activities found."
            return [{"type": "text", "text": text}]

        elif name == "get_tips":
            limit = min(arguments.get("limit", 20), 100)
            q = "SELECT * FROM contexts WHERE type = 'tip' ORDER BY id DESC LIMIT ?"
            rows = [_slim_row(dict(r), "tip") for r in conn.execute(q, [limit]).fetchall()]
            text = json.dumps(rows, ensure_ascii=False, indent=2) if rows else "No tips found."
            return [{"type": "text", "text": text}]

        elif name == "search_context":
            query = arguments.get("query", "")
            type_filter = arguments.get("type", "")
            limit = min(arguments.get("limit", 20), 100)
            allowed = ("todo", "activity", "tip")
            q = "SELECT * FROM contexts WHERE (content LIKE ? OR title LIKE ?)"
            params = [f"%{query}%", f"%{query}%"]
            if type_filter and type_filter in allowed:
                q += " AND type = ?"
                params.append(type_filter)
            else:
                placeholders = ",".join(["?"] * len(allowed))
                q += f" AND type IN ({placeholders})"
                params.extend(allowed)
            q += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            rows = [_slim_row(dict(r), dict(r)["type"]) for r in conn.execute(q, params).fetchall()]
            text = json.dumps(rows, ensure_ascii=False, indent=2) if rows else f"No results for '{query}'."
            return [{"type": "text", "text": text}]

        else:
            return [{"type": "text", "text": f"Unknown tool: {name}"}]
    finally:
        conn.close()


def _handle_mcp_jsonrpc(body: dict) -> Optional[dict]:
    """Handle a single MCP JSON-RPC request. Returns response dict or None for notifications."""
    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": MCP_CAPABILITIES,
            "serverInfo": MCP_SERVER_INFO,
        }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            content = _mcp_call_tool(tool_name, arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": content}}
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
            }

    elif method.startswith("notifications/"):
        return None

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    else:
        return {
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


@app.post("/mcp/message")
async def mcp_message(request: Request):
    """MCP Streamable HTTP endpoint"""
    auth = request.headers.get("authorization", "")
    if AUTH_TOKEN:
        token = ""
        if auth.startswith("Bearer "):
            token = auth[7:]
        if token != AUTH_TOKEN:
            return JSONResponse(status_code=403, content={"error": "Invalid token"})

    body = await request.json()
    result = _handle_mcp_jsonrpc(body)

    if result is None:
        return JSONResponse(status_code=204, content=None)

    return JSONResponse(content=result, headers={
        "Content-Type": "application/json",
    })


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
tr.clickable{cursor:pointer;transition:background .15s}
tr.clickable:hover{background:rgba(59,130,246,.08)}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:100}
.overlay.show{display:block}
.slide-panel{position:fixed;top:0;right:-480px;width:480px;max-width:90vw;height:100vh;background:var(--card);border-left:1px solid var(--border);z-index:101;transition:right .25s ease;display:flex;flex-direction:column}
.slide-panel.show{right:0}
.panel-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border);flex-shrink:0}
.panel-header h3{font-size:1rem}
.panel-close{background:transparent;border:none;color:var(--muted);font-size:1.4rem;cursor:pointer;padding:4px 8px;border-radius:4px;transition:.2s}
.panel-close:hover{color:var(--red);background:rgba(239,68,68,.1)}
.panel-body{flex:1;overflow-y:auto;padding:20px}
.detail-field{margin-bottom:16px}
.detail-label{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}
.detail-value{font-size:.85rem;line-height:1.6;white-space:pre-wrap;word-break:break-word}
.detail-value.content-block{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;max-height:300px;overflow-y:auto}
.detail-value code{background:var(--bg);padding:1px 4px;border-radius:3px;font-size:.8rem}
.detail-meta{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;font-family:'Cascadia Code','Fira Code',monospace;font-size:.75rem;max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
.panel-actions{padding:12px 20px;border-top:1px solid var(--border);display:flex;gap:8px;flex-shrink:0}
.panel-actions button{padding:6px 14px;border-radius:6px;font-size:.8rem;cursor:pointer;transition:.2s}
.btn-copy{background:var(--accent);color:#fff;border:none}
.btn-copy:hover{opacity:.85}
.btn-delete{background:transparent;color:var(--red);border:1px solid var(--red)}
.btn-delete:hover{background:rgba(239,68,68,.1)}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--green);color:#fff;padding:8px 20px;border-radius:8px;font-size:.85rem;z-index:200;opacity:0;transition:opacity .3s}
.toast.show{opacity:1}
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

<div class="overlay" id="overlay" onclick="closePanel()"></div>
<div class="slide-panel" id="slide-panel">
  <div class="panel-header">
    <h3 id="panel-title"></h3>
    <button class="panel-close" onclick="closePanel()">&times;</button>
  </div>
  <div class="panel-body" id="panel-body"></div>
  <div class="panel-actions" id="panel-actions"></div>
</div>
<div class="toast" id="toast"></div>

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
    detail: '详情',
    copyContent: '复制内容',
    deleteItem: '删除',
    copied: '已复制',
    deleted: '已删除',
    confirmDelete: '确定删除这条数据吗？',
    fieldId: 'ID',
    fieldType: '类型',
    fieldTitle: '标题',
    fieldContent: '内容',
    fieldSource: '来源',
    fieldTime: '时间',
    fieldTags: '标签',
    fieldMetadata: '元数据',
    fieldContextType: '上下文类型',
    fieldConfidence: '置信度',
    fieldImportance: '重要度',
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
    detail: 'Detail',
    copyContent: 'Copy Content',
    deleteItem: 'Delete',
    copied: 'Copied',
    deleted: 'Deleted',
    confirmDelete: 'Are you sure you want to delete this item?',
    fieldId: 'ID',
    fieldType: 'Type',
    fieldTitle: 'Title',
    fieldContent: 'Content',
    fieldSource: 'Source',
    fieldTime: 'Time',
    fieldTags: 'Tags',
    fieldMetadata: 'Metadata',
    fieldContextType: 'Context Type',
    fieldConfidence: 'Confidence',
    fieldImportance: 'Importance',
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

let cachedItems = [];

async function loadData(){
  const type = document.getElementById('filter-type').value;
  const d = await api(`/api/contexts?limit=${pageSize}&offset=${page*pageSize}${type?'&type='+type:''}`);
  totalRecords = d.total;
  cachedItems = d.items || [];
  const el = document.getElementById('data-table');
  if(!cachedItems.length){el.innerHTML=`<div class="empty">${t().noData}</div>`;document.getElementById('pagination').innerHTML='';return;}
  const esc = s => s ? s.replace(/</g,'&lt;').replace(/>/g,'&gt;') : '-';
  el.innerHTML=`<table><thead><tr><th>${t().thId}</th><th>${t().thType}</th><th>${t().thTitle}</th><th>${t().thContent}</th><th>${t().thSource}</th><th>${t().thTime}</th></tr></thead><tbody>${
    cachedItems.map((r,i)=>`<tr class="clickable" onclick="openPanel(${i})"><td>${r.id}</td><td><span class="badge">${typeName(r.type)}</span></td><td>${esc(r.title)}</td><td>${esc((r.content||'').substring(0,80))}</td><td>${esc(r.source)}</td><td>${r.client_ts||r.created_at||'-'}</td></tr>`).join('')
  }</tbody></table>`;
  const pages = Math.ceil(totalRecords/pageSize);
  document.getElementById('pagination').innerHTML=`
    <button onclick="page=Math.max(0,page-1);loadData()" ${page<=0?'disabled':''}>${t().prev}</button>
    <span>${t().page}${page+1}${t().of}${pages}${t().pages} (${totalRecords}${t().total})</span>
    <button onclick="page++;loadData()" ${page>=pages-1?'disabled':''}>${t().next}</button>`;
}

function openPanel(idx) {
  const item = cachedItems[idx];
  if(!item) return;
  const T = t();
  document.getElementById('panel-title').textContent = `${T.detail} #${item.id}`;
  const esc = s => (s||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  let metaHtml = '';
  if(item.metadata) {
    try {
      const parsed = typeof item.metadata === 'string' ? JSON.parse(item.metadata) : item.metadata;
      metaHtml = `<div class="detail-field"><div class="detail-label">${T.fieldMetadata}</div><div class="detail-meta">${JSON.stringify(parsed, null, 2)}</div></div>`;
    } catch(e) {
      metaHtml = `<div class="detail-field"><div class="detail-label">${T.fieldMetadata}</div><div class="detail-meta">${esc(String(item.metadata))}</div></div>`;
    }
  }
  document.getElementById('panel-body').innerHTML = `
    <div class="detail-field"><div class="detail-label">${T.fieldType}</div><div class="detail-value"><span class="badge">${typeName(item.type)}</span></div></div>
    ${item.title ? `<div class="detail-field"><div class="detail-label">${T.fieldTitle}</div><div class="detail-value">${esc(item.title)}</div></div>` : ''}
    <div class="detail-field"><div class="detail-label">${T.fieldContent}</div><div class="detail-value content-block" id="detail-content">${esc(item.content)}</div></div>
    ${item.source ? `<div class="detail-field"><div class="detail-label">${T.fieldSource}</div><div class="detail-value">${esc(item.source)}</div></div>` : ''}
    ${item.context_type ? `<div class="detail-field"><div class="detail-label">${T.fieldContextType}</div><div class="detail-value">${esc(item.context_type)}</div></div>` : ''}
    ${item.tags ? `<div class="detail-field"><div class="detail-label">${T.fieldTags}</div><div class="detail-value">${esc(item.tags)}</div></div>` : ''}
    ${item.confidence != null ? `<div class="detail-field"><div class="detail-label">${T.fieldConfidence}</div><div class="detail-value">${item.confidence}</div></div>` : ''}
    ${item.importance != null ? `<div class="detail-field"><div class="detail-label">${T.fieldImportance}</div><div class="detail-value">${item.importance}</div></div>` : ''}
    <div class="detail-field"><div class="detail-label">${T.fieldTime}</div><div class="detail-value">${item.client_ts || item.created_at || '-'}</div></div>
    ${metaHtml}
  `;
  document.getElementById('panel-actions').innerHTML = `
    <button class="btn-copy" onclick="copyContent(${idx})">${T.copyContent}</button>
    <button class="btn-delete" onclick="deleteItem(${item.id})">${T.deleteItem}</button>
  `;
  document.getElementById('overlay').classList.add('show');
  document.getElementById('slide-panel').classList.add('show');
}

function closePanel() {
  document.getElementById('overlay').classList.remove('show');
  document.getElementById('slide-panel').classList.remove('show');
}

function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(()=>el.classList.remove('show'), 2000);
}

function copyContent(idx) {
  const item = cachedItems[idx];
  if(!item) return;
  navigator.clipboard.writeText(item.content || '').then(()=>showToast(t().copied));
}

async function deleteItem(id) {
  if(!confirm(t().confirmDelete)) return;
  await api(`/api/contexts/${id}`, {method:'DELETE'});
  closePanel();
  showToast(t().deleted);
  loadData();
}

document.addEventListener('keydown', e => { if(e.key==='Escape') closePanel(); });

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
