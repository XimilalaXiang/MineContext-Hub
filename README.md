# MineContext Hub

将 [MineContext](https://github.com/volcengine/MineContext) 桌面端采集的上下文数据汇聚到云端的轻量级中转服务。

## 功能

- 接收来自 MineContext Windows 客户端的上下文数据
- Web 管理界面（中英文双语切换）
- 按数据类型开关采集控制
- RESTful API 支持数据写入、查询、统计
- SQLite 持久化存储
- Docker 一键部署

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/XimilalaXiang/MineContext-Hub.git
cd MineContext-Hub

# 启动（Docker）
docker compose up -d --build
```

默认端口：`8000`（容器内） → 可自行映射到宿主机端口。

## 配置

通过环境变量配置（见 `docker-compose.yml`）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AUTH_TOKEN` | API 认证 Token | 空（无认证） |
| `DB_PATH` | SQLite 数据库路径 | `/data/context.db` |
| `SETTINGS_PATH` | 设置文件路径 | `/data/settings.json` |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | Web 管理界面 |
| `GET` | `/health` | 健康检查 |
| `GET` | `/stats` | 统计信息 |
| `POST` | `/ingest` | 写入单条数据 |
| `POST` | `/ingest/batch` | 批量写入 |
| `GET` | `/api/contexts` | 查询数据 |
| `GET` | `/api/settings` | 获取采集设置 |
| `POST` | `/api/settings` | 更新采集设置 |
| `DELETE` | `/api/contexts/{id}` | 删除单条数据 |

所有需认证的接口使用 `Authorization: Bearer <TOKEN>` 请求头。

## 数据类型

| 类型 | 说明 |
|------|------|
| `screenshot` | 截图 |
| `vault` | 知识库 |
| `todo` | 待办 |
| `activity` | 活动 |
| `tip` | 提示 |
| `message` | 消息 |
| `conversation` | 对话 |
| `monitoring` | 监控 |
| `entity` | 实体 |
| `knowledge` | 知识 |
| `custom` | 自定义 |

## License

MIT
