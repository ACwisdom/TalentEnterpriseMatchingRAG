# recruitment-api

可独立拆出为单独 Git 仓库的 **Spring Boot 3.3 + Java 21** 招聘匹配 REST 服务，默认嵌在本仓库 `java/recruitment-api/` 下。

## 要求

- JDK **21**
- Maven **3.9+**（或本目录下的 Maven Wrapper，见下文）

## 构建与测试

```bash
cd java/recruitment-api
mvn test
# 若已生成 wrapper：
./mvnw test   # Linux / macOS
mvnw.cmd test # Windows
```

## 运行

```bash
mvn spring-boot:run
# 默认未设置 SERVICE_API_KEY 时不校验鉴权（便于本地开发）；生产务必设置密钥。
```

- **Swagger UI**：<http://localhost:8080/swagger-ui.html>
- **OpenAPI JSON**：<http://localhost:8080/v3/api-docs>

## 环境变量

| 变量 | 说明 |
|------|------|
| `SERVICE_API_KEY` | 设置后，`/api/v1/**` 需 `X-API-Key: <值>` 或 `Authorization: Bearer <值>` |
| `SPRING_DATASOURCE_URL` / `SPRING_DATASOURCE_USERNAME` / `SPRING_DATASOURCE_PASSWORD` | 使用 `--spring.profiles.active=postgres` 时连接 PostgreSQL |

## 配置说明

- 默认 **H2** 内存库（`MODE=PostgreSQL`），Flyway 管理 schema。
- 激活 **`postgres`** profile 时使用 PostgreSQL（见 `application.yml` 文档段）。
- 统一错误体：`{ "code", "message", "details" }`（`GlobalExceptionHandler`）。
- 写操作 POST 支持 **`Idempotency-Key`**，响应在 24 小时内从表 `idempotency_record` 重放。
- 响应头回显 **`X-Correlation-Id`**（若请求未带则生成）。

## 与 Python / LangGraph

HTTP 契约见仓库根目录 `contracts/recruitment-api-v1.openapi.yaml`；集成说明见 `docs/java-langgraph-integration.md`。
