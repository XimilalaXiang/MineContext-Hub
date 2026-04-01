#!/usr/bin/env python3
"""
MineContext → Context Hub 增量同步脚本
在 Windows 上运行，定时读取 MineContext 本地 SQLite 数据库，
将新数据推送到云端 Context Hub。
"""

import json
import logging
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

CONFIG_FILE = Path(__file__).parent / "config.json"
STATE_FILE = Path(__file__).parent / "sync_state.json"

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("minecontext-sync")

TABLE_DEFS = {
    "vaults": {
        "type": "vault",
        "id_col": "id",
        "time_col": "created_at",
        "fields": ["id", "title", "summary", "content", "tags",
                    "document_type", "created_at", "updated_at"],
        "content_field": "content",
        "title_field": "title",
    },
    "todo": {
        "type": "todo",
        "id_col": "id",
        "time_col": "created_at",
        "fields": ["id", "content", "created_at", "start_time",
                    "end_time", "status", "urgency", "assignee", "reason"],
        "content_field": "content",
        "title_field": None,
    },
    "activity": {
        "type": "activity",
        "id_col": "id",
        "time_col": "start_time",
        "fields": ["id", "title", "content", "resources",
                    "metadata", "start_time", "end_time"],
        "content_field": "content",
        "title_field": "title",
    },
    "tips": {
        "type": "tip",
        "id_col": "id",
        "time_col": "created_at",
        "fields": ["id", "content", "created_at"],
        "content_field": "content",
        "title_field": None,
    },
    "conversations": {
        "type": "conversation",
        "id_col": "id",
        "time_col": "created_at",
        "fields": ["id", "title", "user_id", "page_name",
                    "status", "metadata", "created_at", "updated_at"],
        "content_field": "title",
        "title_field": "title",
    },
    "messages": {
        "type": "message",
        "id_col": "id",
        "time_col": "created_at",
        "fields": ["id", "conversation_id", "role", "content",
                    "status", "token_count", "created_at"],
        "content_field": "content",
        "title_field": None,
    },
    "monitoring_data_stats": {
        "type": "monitoring",
        "id_col": "id",
        "time_col": "created_at",
        "fields": ["id", "time_bucket", "data_type", "count",
                    "context_type", "metadata", "created_at"],
        "content_field": "data_type",
        "title_field": "data_type",
    },
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        log.error("配置文件不存在: %s", CONFIG_FILE)
        log.error("请复制 config.example.json 为 config.json 并填写配置")
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                          encoding="utf-8")


def find_minecontext_db(config: dict) -> Optional[Path]:
    """查找 MineContext 数据库文件"""
    explicit = config.get("db_path")
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        log.warning("配置的数据库路径不存在: %s", explicit)

    candidates = []
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    userprofile = os.environ.get("USERPROFILE", "")

    for base in [appdata, localappdata, userprofile]:
        if not base:
            continue
        candidates.extend([
            Path(base) / "MineContext" / "persist" / "sqlite" / "app.db",
            Path(base) / "minecontext" / "persist" / "sqlite" / "app.db",
            Path(base) / ".minecontext" / "persist" / "sqlite" / "app.db",
            Path(base) / "MineContext" / "app.db",
        ])

    for c in candidates:
        if c.exists():
            log.info("找到 MineContext 数据库: %s", c)
            return c

    log.error("未找到 MineContext 数据库，请在 config.json 中手动指定 db_path")
    return None


def open_db_readonly(db_path: Path) -> sqlite3.Connection:
    """以只读方式打开 SQLite（通过复制临时文件避免锁冲突）"""
    tmp_path = db_path.parent / f".sync_copy_{db_path.name}"
    shutil.copy2(str(db_path), str(tmp_path))
    conn = sqlite3.connect(str(tmp_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def get_table_names(conn: sqlite3.Connection) -> set:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def fetch_new_rows(conn: sqlite3.Connection, table: str,
                   tdef: dict, last_id: int) -> List[dict]:
    """获取 id > last_id 的新数据"""
    cols = ", ".join(tdef["fields"])
    sql = f"SELECT {cols} FROM {table} WHERE {tdef['id_col']} > ? ORDER BY {tdef['id_col']} ASC LIMIT 500"
    rows = conn.execute(sql, (last_id,)).fetchall()
    return [dict(r) for r in rows]


def row_to_ingest_payload(row: dict, tdef: dict, table: str) -> dict:
    content_val = row.get(tdef["content_field"]) or ""
    title_val = row.get(tdef["title_field"]) if tdef["title_field"] else None
    time_val = row.get(tdef["time_col"]) or ""

    meta = {}
    for k, v in row.items():
        if k in ("content", "title", "summary"):
            continue
        if v is not None:
            meta[k] = v

    return {
        "type": tdef["type"],
        "content": str(content_val),
        "title": str(title_val) if title_val else None,
        "source": f"minecontext/{table}",
        "context_type": tdef["type"],
        "tags": row.get("tags"),
        "metadata": meta if meta else None,
        "client_timestamp": str(time_val) if time_val else None,
    }


def push_batch(hub_url: str, token: str, payloads: List[dict],
               timeout: int = 30) -> bool:
    url = f"{hub_url.rstrip('/')}/ingest/batch"
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payloads, headers=headers,
                             timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            log.info("推送成功: inserted=%s, skipped=%s",
                     data.get("inserted"), data.get("skipped"))
            return True
        elif resp.status_code == 422:
            log.warning("部分数据类型被禁用: %s", resp.text)
            return True
        else:
            log.error("推送失败 HTTP %s: %s", resp.status_code, resp.text)
            return False
    except requests.RequestException as e:
        log.error("网络错误: %s", e)
        return False


def sync_once(config: dict, state: dict) -> dict:
    """执行一次同步"""
    db_path = find_minecontext_db(config)
    if not db_path:
        return state

    hub_url = config["hub_url"]
    token = config["hub_token"]
    enabled_types = set(config.get("sync_types", list(TABLE_DEFS.keys())))
    batch_size = config.get("batch_size", 100)

    try:
        conn = open_db_readonly(db_path)
    except Exception as e:
        log.error("打开数据库失败: %s", e)
        return state

    existing_tables = get_table_names(conn)
    total_pushed = 0

    for table, tdef in TABLE_DEFS.items():
        if table not in existing_tables:
            continue
        if table not in enabled_types:
            continue

        last_id = state.get(f"last_id_{table}", 0)
        rows = fetch_new_rows(conn, table, tdef, last_id)

        if not rows:
            continue

        log.info("[%s] 发现 %d 条新数据 (last_id=%d)",
                 table, len(rows), last_id)

        payloads = [row_to_ingest_payload(r, tdef, table) for r in rows]

        for i in range(0, len(payloads), batch_size):
            batch = payloads[i:i + batch_size]
            if push_batch(hub_url, token, batch):
                max_id = rows[min(i + batch_size, len(rows)) - 1][tdef["id_col"]]
                state[f"last_id_{table}"] = max_id
                save_state(state)
                total_pushed += len(batch)
            else:
                log.warning("[%s] 批次推送失败，下次重试", table)
                break

    conn.close()

    tmp_file = db_path.parent / f".sync_copy_{db_path.name}"
    try:
        tmp_file.unlink(missing_ok=True)
    except Exception:
        pass

    if total_pushed > 0:
        log.info("本轮同步完成: 共推送 %d 条数据", total_pushed)
    else:
        log.debug("本轮无新数据")

    return state


def main():
    config = load_config()
    state = load_state()

    interval = config.get("sync_interval_seconds", 60)
    log.info("MineContext Sync 启动")
    log.info("Hub: %s", config["hub_url"])
    log.info("同步间隔: %d 秒", interval)

    while True:
        try:
            state = sync_once(config, state)
        except Exception as e:
            log.exception("同步异常: %s", e)

        time.sleep(interval)


if __name__ == "__main__":
    main()
