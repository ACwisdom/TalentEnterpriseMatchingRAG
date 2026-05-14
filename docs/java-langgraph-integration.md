# Java recruitment-api 与 Python / LangGraph 集成

本仓库将 **Java Spring Boot 服务**（`java/recruitment-api/`）与 **Python LangGraph 工具包**（`langgraph_tools/`）放在同一工作区，便于联调；生产上可拆成两个 Git 仓库，仅通过 HTTP 契约耦合。

## 两仓拆分时的约定

- **契约**：以根目录 `contracts/recruitment-api-v1.openapi.yaml`（OpenAPI 3.1）为准；Java 实现与 `langgraph_tools` 客户端应对齐该文件中的路径与模型。
- **基址**：Python 侧使用环境变量 **`JAVA_API_BASE_URL`**（例如 `http://127.0.0.1:8080`），勿写死主机名。
- **鉴权**（与 Java `SERVICE_API_KEY` 一致）：
  - `X-API-Key: <SERVICE_API_KEY>`，或
  - `Authorization: Bearer <SERVICE_API_KEY>`
- **幂等写**：对 POST 写入可携带 **`Idempotency-Key`**（Java 端 24h 内重放缓存响应）。
- **链路**：可选 **`X-Correlation-Id`**；若省略，服务端会生成并在响应中回显。
- **非 MCP**：本集成路径为普通 REST，不依赖 MCP 服务器。

## 本地联调步骤（摘要）

1. 启动 Java：`cd java/recruitment-api && mvn spring-boot:run`（若启用鉴权则导出 `SERVICE_API_KEY`）。
2. 可选：浏览器打开 `http://127.0.0.1:8080/swagger-ui.html` 核对 OpenAPI。
3. Python：`pip install -r requirements.txt`，设置 `JAVA_API_BASE_URL`，运行示例：
   - `python -m langgraph_tools.example_graph`（需设置 `DEMO_JOB_ID` / `DEMO_CANDIDATE_ID` 等环境变量指向已存在数据）。

## 与主项目 RAG 流水线

`langgraph_tools` 仅封装对招聘 API 的 HTTP 调用与错误映射；人才—企业 RAG 主流程仍在 `src/` 与 `web/`，二者通过你在图或 Agent 中编排的节点衔接。
