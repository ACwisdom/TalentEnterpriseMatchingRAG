# 公网部署说明（境外 + HTTPS + API Key）

面向：在境外 VPS 或 PaaS 上对外提供本项目的 Web 匹配服务，使用 `X-API-Key` 鉴权，域名与 HTTPS 由平台或反向代理提供。

## 环境变量

| 变量 | 说明 |
|------|------|
| `APP_API_KEY` | 单个合法 API Key（与 `APP_API_KEYS` 二选一或同时配置） |
| `APP_API_KEYS` | 多个 Key，逗号分隔 |
| `MIMO_API_KEY` | MiMo 调用密钥（见 `src/config.py`） |
| `RETRIEVAL_MODE` | 可选：`keyword` / `vector` / `hybrid` / `hybrid_legacy`（默认见配置） |
| `REFERENCE_DATE` | 可选，ISO 日期，用于报告时效表述 |
| `WEB_MAX_UPLOAD_BYTES` | 可选，上传简历最大字节数（默认约 15MB） |
| `WEB_DOWNLOAD_TTL_SEC` | 可选，下载令牌在内存中的有效期（默认 3600） |
| `MIMO_USE_STREAM` | 可选：设为 `0`、`false`、`no` 时关闭 MiMo 流式解析，流式匹配接口内对画像/主报告回退为同步请求（默认开启流式） |

不要将 `.env` 或真实 Key 提交到 Git。

### 匹配 API：JSON 与 SSE

- **`POST /api/match`**：multipart 表单（`file`、`top_k`、`use_llm`、`use_llm_for_profile`），返回 JSON（`report_text`、`download_id` 等）。**单次企业检索**，无第二次整 pipeline。
- **`POST /api/match/stream`**：表单字段相同，响应为 **`text/event-stream`**（SSE）。事件为 `data: {JSON}\n\n`，含 `stage`、`token`（增量正文）、`warning`、`error`、最终 **`done`**（含 `download_id`、`report_text`）。首页静态页使用 fetch 流式读取。

**反向代理注意**：Nginx 等对 SSE 默认可能开启响应缓冲，导致前端「卡住一段后一次性吐字」。应对 `/api/match/stream` 关闭缓冲，例如：

```nginx
location /api/match/stream {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;
    proxy_cache off;
    gzip off;
    proxy_read_timeout 3600s;
}
```

Caddy 前接长耗时流式时，可酌情调大 `servers` 下相关超时。Fly.io 边缘到 Machine 若仍有攒包，可在应用前再加一层按上述原则配置的自管反代。

### `X-API-Key` 与 MiMo 的区别

- **`MIMO_API_KEY`**：只放在服务器环境变量里，用于调用大模型，**不要**让用户在网页里填写。
- **`APP_API_KEY` / `X-API-Key`**：用于限制谁可以调你的匹配接口（防刷、防滥用），与 MiMo 无关。
- **本机浏览器**：当请求来自环回地址（`127.0.0.1` 等）时，服务端**不要求**带 `X-API-Key`，便于本地只配 `.env` 即可用。经公网域名或局域网 IP 访问时，若已配置 `APP_API_KEY`，则必须在请求头携带正确的 `X-API-Key`（或由反向代理注入）。

## 数据与向量索引

- 企业表：`data/enterprise_db.xlsx`（或按 `src/config.py` 中路径准备）。
- Chroma 持久化目录：`data/enterprise_vectors`（容器内需 **Volume** 挂载，否则每次重建镜像/实例会丢索引）。
- 若卷为空，需在镜像内或启动前执行：`python -m src.build_enterprise_index`（必要时加 `--force`），详见项目内索引构建说明。

`sentence-transformers` 首次运行会下载嵌入模型，冷启动较慢；生产环境建议在镜像构建阶段预热缓存或使用挂载缓存目录。

## 本地 Docker 运行

在项目根目录：

```bash
docker build -t talent-match-web .
docker run --rm -p 8000:8000 ^
  -e APP_API_KEY=your-secret-key ^
  -e MIMO_API_KEY=your-mimo-key ^
  -v talent_chroma:/app/data/enterprise_vectors ^
  talent-match-web
```

访问 `http://127.0.0.1:8000/`。健康检查：`GET /health`（无需 API Key）。

Windows 本机若遇 **Internal Server Error**，多为控制台编码问题；`web/main.py` 已在启动时尽量把 stdout/stderr 设为 UTF-8，仍异常时可设置环境变量 `PYTHONUTF8=1` 或 `PYTHONIOENCODING=utf-8` 后再启动 `uvicorn`。

## Fly.io（推荐思路）

仓库根目录提供 [`fly.toml`](fly.toml)（Machines / `[http_service]` 风格，`fly deploy` 可直接使用）。

### `fly launch` 与手写 `fly.toml`

- **`fly launch`**：交互式创建应用、生成或合并 `fly.toml`、可选首启 Machine。适合从零开始；若仓库已有 `fly.toml`，按提示选择保留/合并字段，并核对 **`app` 名称**、`primary_region`、挂载路径是否与本文一致。
- **手写 / 随仓库提交 `fly.toml`**：适合 CI 与可复现部署。创建应用后执行 `fly apps create <你的唯一应用名>`，再把 `fly.toml` 里的 `app = "..."` 改成该名称（默认占位为 `talent-enterprise-matching-rag`，请改为 Fly 全局唯一 slug；也可用 `talent-match-rag` 等自行命名）。

`primary_region` 在 `fly.toml` 中默认为 **`sin`（新加坡）**；可改为 **`nrt`（东京）** 等，但须与 **Volume 所在区域一致**。

### Volume 与挂载（关键）

Chroma 数据写在 `data/enterprise_vectors`（见 `src/config.py`）。在 Fly 上应使用 **Volume** 持久化该目录。

1. 在**与 `primary_region` 相同**的区域创建卷（名称需与 `fly.toml` 中 `[[mounts]]` 的 `source` 一致，占位为 `enterprise_vectors_data`）：

   ```bash
   fly volumes create enterprise_vectors_data --region sin --size 3
   ```

   若应用使用 `nrt`，将 `--region` 改为 `nrt`。

2. **`fly.toml` 中仅挂载 `/app/data/enterprise_vectors`**（本仓库已如此配置）。  
   **不要**把 Volume 挂到 `/app/data` 整目录：否则空卷会**遮盖**镜像里通过 `COPY data` 带入的 `data/default/`（含 `/demo` 演示页）和 `data/enterprise_db.xlsx`，导致 Demo 缺失或匹配读不到企业表。

3. 镜像构建上下文须包含 **`data/default/`** 与 **`data/enterprise_db.xlsx`**（本仓库 `Dockerfile` 已 `COPY data ./data`，且 `.dockerignore` 未排除它们）。若你本地改动了 `.dockerignore`，请勿排除上述路径。

### 密钥与环境

使用 CLI 注入敏感变量（勿写入 `fly.toml` 或 Git）：

```bash
fly secrets set APP_API_KEY="你的接口密钥" MIMO_API_KEY="你的MiMo密钥"
```

按需追加：`APP_API_KEYS`、`RETRIEVAL_MODE`、`REFERENCE_DATE`、`WEB_MAX_UPLOAD_BYTES` 等（见上文「环境变量」表）。

### 部署、证书与 DNS

```bash
fly deploy
```

- 默认可获得 `https://<app>.fly.dev`。
- 自定义域名：`fly certs add example.com`，按输出在 DNS 提供商处添加 **A/AAAA** 或 **CNAME** 记录；证书就绪后 Fly 边缘自动 HTTPS。

### 验证

- 健康检查：`curl -sS https://你的域名/health`（或 `https://<app>.fly.dev/health`），应返回 200 JSON。
- Demo 页：`https://你的域名/demo`（公开只读，不经过 `X-API-Key` 的业务上传流程）。

### 首启空卷：构建企业向量索引

新 Volume 挂载后 `enterprise_vectors` 为空，需在**已部署且能访问卷**的 Machine 上执行一次索引构建（需网络以下载嵌入模型等）：

```bash
fly ssh console -C "python -m src.build_enterprise_index"
```

若需重建可加 `--force`。首启冷启动较慢属正常现象。

### 安全说明

- **`/demo` 为公开只读展示**；勿在 `data/default` 中存放密钥或隐私生产数据。
- **`/health`** 匿名便于探活；**`/api/*`** 在公网访问时应配置并要求 `X-API-Key`（见上文）。

### 其他

- 当前下载令牌 `download_id` 存在**进程内存**中，多实例或机器重启后链接失效；单实例 + 单副本可接受。
- `fly.toml` 中 `auto_stop_machines = "stop"` 与 `auto_start_machines = true` 可在无流量时停机会话以节省成本；首次请求会有冷启动延迟。

费用大致包含：Fly 机器规格与 Volume + 域名年费 + **MiMo 按调用计费**（建议在厂商控制台设置预算/告警）。

## 备选：境外 VPS + Docker + Caddy

1. 安装 Docker，将同上镜像运行在同一主机，`docker compose` 中挂载数据卷。
2. 安装 [Caddy](https://caddyserver.com/)，示例 Caddyfile：

```text
your-domain.com {
    reverse_proxy 127.0.0.1:8000
}
```

3. 将域名 DNS **A/AAAA** 记录指向 VPS 公网 IP，Caddy 会自动申请 Let’s Encrypt 证书。

## 安全与滥用防护

- 所有 `/api/*`（除你自行放开的接口）应要求有效 `X-API-Key`；`/health` 可匿名便于探活。
- 上传大小与请求超时已在应用层部分限制；可在边缘（Caddy/Fly）再加速率限制。
- API Key 泄露即等同账号泄露，应定期轮换。

## 验收清单

- `https://你的域名/health` 返回 200 且 JSON 含 `status`。
- `https://你的域名/demo` 能打开双栏 Demo；列表来自 `data/default/input` 与 `output`。
- `https://你的域名/` 能打开上传页；公网访问下错误 Key 对 `/api/match` 与 `/api/match/stream` 返回 401。
- 正确 Key 下能流式生成报告文本并下载 Word（或 JSON 路径 `/api/match` 一次返回）。
- 容器重启后，**仅**挂载卷目录 `enterprise_vectors` 中的索引仍在，检索行为一致；`data/default` 与 `enterprise_db.xlsx` 仍以镜像内文件为准（勿用整盘挂载覆盖 `/app/data`）。
