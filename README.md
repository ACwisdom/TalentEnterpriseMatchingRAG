# TalentEnterpriseMatchingRAG

人才—企业智能匹配与报告生成（RAG）：从企业库检索候选企业，组装提示词，可选调用 **小米 MiMo** 生成报告并导出 **Word**。

**项目简介（约 300 字）**见 [`docs/项目介绍.md`](docs/项目介绍.md)。

**招聘匹配 REST API（Java）与 LangGraph 工具**：见 [`java/recruitment-api/README.md`](java/recruitment-api/README.md)、[`langgraph_tools/`](langgraph_tools/) 与 [`docs/java-langgraph-integration.md`](docs/java-langgraph-integration.md)；OpenAPI 手维护契约见 [`contracts/recruitment-api-v1.openapi.yaml`](contracts/recruitment-api-v1.openapi.yaml)。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| 企业检索 | 关键词 / 向量 / 混合（RRF），配置见 `src/config.py` 中 `RETRIEVAL_MODE` |
| 向量索引 | Chroma + `sentence-transformers`，持久化目录 `data/enterprise_vectors` |
| 简历 | 支持 PDF、DOCX、TXT（`src/resume_processor.py`） |
| 大模型 | MiMo 生成匹配报告、人才画像；可选微信截图高级画像（`docs/高级人才画像功能说明.md`） |
| Web | FastAPI：`/` 上传匹配（`POST /api/match/stream` 流式 SSE + `POST /api/match` JSON），`/demo` 固定目录展示，`/health` 探活（`web/main.py`） |
| 部署 | Docker、`fly.toml`，说明见 [`docs/deploy-public.md`](docs/deploy-public.md) |

---

## 环境要求

- Python **3.11+**（与 `Dockerfile` 一致）
- Windows 建议设置 `PYTHONUTF8=1` 或 `PYTHONIOENCODING=utf-8`，避免控制台编码导致 Web 500

---

## 快速开始

```bash
cd TalentEnterpriseMatchingRAG
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

复制 `.env` 模板（自行创建），至少配置：

| 变量 | 用途 |
|------|------|
| `MIMO_API_KEY` | 调用 MiMo（可选，不用 LLM 时可不配） |
| `APP_API_KEY` | Web 接口 `X-API-Key`（公网访问 `/api/match`、`/api/match/stream` 需要） |
| `MIMO_USE_STREAM` | 可选：`0` / `false` / `no` 关闭 MiMo 流式，流式接口内回退为同步 `chat`（默认开启流式） |

准备 **`data/enterprise_db.xlsx`**，首次构建向量索引：

```bash
python -m src.build_enterprise_index
```

### 命令行批量报告

```bash
python scripts/run_match_reports.py
python scripts/run_match_reports.py --light
```

### Web 本地运行

```bash
set APP_API_KEY=你的密钥
uvicorn web.main:app --host 127.0.0.1 --port 8000
```

浏览器访问 `http://127.0.0.1:8000/`；固定 Demo：`http://127.0.0.1:8000/demo`。

首页使用 **fetch 读取 SSE**（`text/event-stream`）边生成边显示报告；公网若在 Nginx/Caddy 后部署，请关闭响应缓冲（例如 Nginx `proxy_buffering off`），并酌情调大 `read_timeout`，否则流式可能被攒包或中途断开。详见 [`docs/deploy-public.md`](docs/deploy-public.md)。

### 测试

```bash
pytest tests/
```

---

## 目录结构（节选）

```
src/                 核心业务：检索、流水线、LLM、Word 导出
web/                 FastAPI 与静态页
java/recruitment-api Java REST v1（企业/职位/人才/推荐/沟通/出站消息/提醒），见该目录 README
langgraph_tools/     调用 Java 的 httpx 客户端与 LangGraph 示例（无 MCP）
contracts/           OpenAPI 契约快照（与 Java 同步维护）
prompts/             系统提示词
data/                企业表、向量库、输入输出、default 演示
scripts/             批处理、静态假页生成等
docs/                部署说明、高级画像、项目介绍、Java 联调
fly.toml             Fly.io 部署配置
Dockerfile
TalentEnterpriseMatchingRAG_project_deck.pptx   项目介绍 PPT（可运行 scripts/generate_project_pptx.py 重新生成）
TalentEnterpriseMatchingRAG_project_brief_feishu.docx   飞书用 Word 说明（可运行 scripts/generate_feishu_project_docx.py 重新生成）
```

---

## 文档索引

- [Java API 与 LangGraph 联调](docs/java-langgraph-integration.md)
- 根目录 **TalentEnterpriseMatchingRAG_project_deck.pptx**：项目介绍幻灯片（可用 `python scripts/generate_project_pptx.py` 重新生成，需 `pip install python-pptx`）
- [高级人才画像](docs/高级人才画像功能说明.md)
- [项目介绍（约 300 字）](docs/项目介绍.md)
- [视频演示解说词](docs/视频演示解说词.md)

---

## 许可证

未在仓库中统一声明许可证前，默认 **保留所有权利**；如需开源请自行补充 `LICENSE` 并更新本段。
