# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Taipei City Dashboard is a data visualization platform by Taipei Urban Intelligence Center (TUIC). It's a monorepo with three sub-projects:

- **Taipei-City-Dashboard-FE** — Vue 3 frontend (Vite, Pinia, Mapbox GL)
- **Taipei-City-Dashboard-BE** — Go backend (Gin, GORM, PostgreSQL, Redis)
- **Taipei-City-Dashboard-DE** — Data engineering pipelines (Airflow DAGs, Google Cloud Composer)

## Build & Run Commands

### Frontend (`Taipei-City-Dashboard-FE/`)
```bash
npm ci                  # install dependencies
npm run dev             # local dev server (Vite)
npm run build           # lint + production build
npm run build:test      # lint + test-mode build
npm run lint            # ESLint with auto-fix
```

### Backend (`Taipei-City-Dashboard-BE/`)
```bash
go build -v ./...       # build
go run main.go          # start server (default :8080)
go run main.go migrateDB      # create/update manager DB schema
go run main.go initDashboard  # insert sample dashboard data
```

### Docker (from `docker/`)
```bash
# Requires external bridge network: br_dashboard
docker network create --driver=bridge --subnet=192.168.128.0/24 --gateway=192.168.128.1 br_dashboard
docker compose up               # full stack (nginx, FE, BE, vector-db-upgrade)
docker compose -f docker-compose-db.yaml up    # databases only
docker compose -f docker-compose-init.yaml up   # init/seed databases
```

## Architecture

### Backend Structure

The backend uses Cobra for CLI commands (`cmd/root.go`) and Gin for HTTP routing.

- **`global/`** — All config loaded from env vars (DB, Redis, Qdrant, TWCC AI, JWT). See `global.go` for config structs and `consts.go` for rate limits and API version.
- **`app/app.go`** — Entry point: connects DBs, Redis, initializes ONNX model session, starts Gin server via `endless`.
- **`app/routes/router.go`** — All API routes under `/api/v1/`. Route groups: auth, user, component, dashboard, issue, incident, contributor, chatlog, vector, AI.
- **`app/controllers/`** — Request handlers, one file per domain.
- **`app/models/`** — GORM models and database operations. Two PostgreSQL databases:
  - **DBManager** — users, auth, dashboards config, components config, issues, incidents, chat logs
  - **DBDashboard** — actual statistical/city data for components
- **`app/middleware/`** — JWT validation, rate limiting, admin checks, CORS headers, XFF sanitization.
- **`app/services/ai/`** — AI chat service with TWCC LLM provider (SSE streaming), tool calling registry.
- **`app/cache/`** — Redis client.
- **`logs/`** — Custom logging wrapper.

### Frontend Structure

Vue 3 with Composition API, Vite bundler, Pinia state management.

- **`src/store/`** — Pinia stores: `contentStore` (dashboards/components), `mapStore` (Mapbox state), `authStore` (JWT/user), `dialogStore` (modals), `adminStore` (admin views), `chatStore` (AI chat).
- **`src/views/`** — Page-level components: DashboardView, MapView, ComponentView, EmbedView, plus admin views.
- **`src/components/`** — UI components organized by: `dialogs/`, `map/`, `utilities/bars|forms|miscellaneous`, `charts/`, `icons/`.
- **`src/dashboardComponent/`** — Self-contained dashboard component system with 15+ chart types (Bar, Column, Donut, Heatmap, Radar, Treemap, Metro, Gauge, etc.). Each chart is a Vue component.
- **`src/router/`** — Vue Router config with auth guards, mobile redirects, admin route protection. `axios.js` for HTTP client config.
- **`src/assets/`** — Utility functions (geo calculations, color conversion, data timeframe), Mapbox configs, ApexCharts configs, global CSS styles.

### Key Patterns

- **Two-database pattern**: The BE connects to two separate PostgreSQL databases (Manager for config/users, Dashboard for city data). `models.ConnectToDatabases("MANAGER", "DASHBOARD")` accepts variadic DB names.
- **Rate limiting**: Every route group has per-API and total request limits configured in `global/consts.go`.
- **Auth flow**: ISSO/TaipeiPass OAuth for production; JWT-based session management.
- **Map integration**: Mapbox GL with deck.gl overlays, Threebox for 3D, extensive GeoJSON data in `public/mapData/`.
- **AI features**: Vector search via Qdrant + ONNX embeddings, LLM chat via TWCC API with SSE streaming and tool calling.

## Code Style

- **Frontend**: Tabs for indentation (enforced by ESLint). No `console.log` (only `console.warn`/`console.error`). ESLint flat config with Vue plugin.
- **Backend**: Standard Go formatting. Module name is `TaipeiCityDashboardBE`.
- **Language**: Code comments and UI are primarily in Chinese (Traditional). Variable names and API paths are in English.

## Environment Variables

Frontend env vars are prefixed with `VITE_`. Template at `Taipei-City-Dashboard-FE/.env.template`. Key vars: `VITE_API_URL`, `VITE_MAPBOXTOKEN`, `VITE_MAPBOXTILE`.

Backend config is entirely env-var driven (see `Taipei-City-Dashboard-BE/global/global.go`). Key groups: `DB_MANAGER_*`, `DB_DASHBOARD_*`, `REDIS_*`, `QDRANT_*`, `TWCC_*`, `JWT_SECRET`, `GIN_PORT`.

## 新增組件最佳實踐（源自官方文件 + 實作經驗）

參考文件：https://citydashboard.taipei/documentation/

### 組件結構（Component Config）

每個組件由 4 張 DB 表組成，全部在 DBManager 中：
- `components` — id, index (唯一英文代碼), name
- `component_charts` — color[], types[] (支援的圖表類型), unit
- `component_maps` — 每個地圖圖層一筆，含 type/source/paint/property
- `query_charts` — 每個城市一筆，含 SQL 查詢、時間設定、資料源

**City 欄位**：`taipei`（臺北市）或 `metrotaipei`（雙北整合）。相同 ID 的組件在不同城市共用 name 和 chart_config。

**Query Types**：`two_d`（二維）、`three_d`（三維）、`time`（時序）、`percent`（百分比）、`map_legend`（地圖圖例）

**time_from 有效值**：`static`、`demo`、`current`、`day_ago`、`week_ago`、`month_ago`、`quarter_ago`、`halfyear_ago`、`year_ago`、`twoyear_ago`、`fiveyear_ago`、`tenyear_ago`、`max`、`day_start`、`week_start`、`month_start`、`quarter_start`、`year_start`

### 新增 Airflow DAG 規範

所有 DAG 遵循 `CommonDag` 模式：
```python
from airflow import DAG
from operators.common_pipeline import CommonDag

def _RXXXX(**kwargs):
    # 所有 import 和邏輯必須在函式內（不可在模組層級）
    # 唯二例外：from airflow import DAG 和 from operators.common_pipeline import CommonDag
    ...

dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="RXXXX")
dag.create_dag(etl_func=_RXXXX)
```

**ETL kwargs**：`dag_infos`、`ready_data_db_uri`、`raw_data_db_uri`、`proxies`、`data_path`

**關鍵工具函式**：
- `utils.load_stage.save_geodataframe_to_postgresql` — 含地理欄位的資料（需 `wkb_geometry` 欄位）
- `utils.load_stage.save_dataframe_to_postgresql` — 無地理欄位的資料
- `utils.load_stage.update_lasttime_in_data_to_dataset_info` — 必須在結尾呼叫
- `utils.transform_geometry.add_point_wkbgeometry_column_to_df` — 從 lng/lat 建立 Point geometry
- `utils.transform_time.convert_str_to_time_format` — 時間字串轉換

**load_behavior**：
- `current+history` — 即時資料（清空 default table + 附加到 history table）
- `replace` — 靜態資料（清空並重寫 default table）
- `append` — 累積資料

### 地圖圖層（Map Layers）

**地圖資料來源**：
1. 靜態 GeoJSON：`/public/mapData/{index}.geojson`
2. API 端點：`/api/v1/component/{id}/geo?city=taipei`（PostGIS → GeoJSON 即時轉換）
3. GeoServer WFS：`/geo_server/taipei_vioc/ows?service=WFS&...`（生產環境）

**Symbol 圖示**：36x36 RGBA PNG，放在 `/public/images/map/{name}.png`，並在 `mapStore.js` 的 `addSymbolSources` 方法中註冊。

**Paint 表達式**：使用 Mapbox GL expression syntax，常用模式：
- `["step", ["get","field"], defaultColor, threshold1, color1, ...]` — 分級著色
- `["interpolate", ["linear"], ["zoom"], zoom1, size1, ...]` — 縮放插值

### Dashboard Icons

使用 Material Design Icons Round（CDN 載入），直接使用 icon name 字串（如 `water_drop`、`engineering`）。

## 雙 AI 協作工作流

### 角色分工

- **Claude Code（本系統）**：規劃者 + 排程器 + 品質閘門
  - 負責：專案規劃、文件撰寫、架構審查、任務拆分、最終合併決策
  - 不負責：直接寫產品程式碼（除非 Codex 失敗需要接手）

- **OpenAI Codex（透過 codex-plugin-cc）**：執行者
  - 負責：程式碼實作、code review、bug 修復、commit & push
  - 不負責：架構決策、文件撰寫、合併決策

### 工作流命令一覽

| 命令 | 執行者 | 用途 |
|------|--------|------|
| `/plan` | Claude Code | 分析 codebase、產出架構與規格文件 |
| `/doc` | Claude Code | 撰寫或更新文件 |
| `/delegate` | Claude Code → Codex | 將任務批次委派給 Codex |
| `/status` | 查詢 Codex | 檢視所有委派任務的狀態 |
| `/collect` | Claude Code ← Codex | 收集 Codex 成果並品質審查 |
| `/review-all` | Codex | 批次 PR review |
| `/patrol` | Claude Code + Codex | 定時巡邏式 PR review（搭配 /loop） |
| `/ship` | 全流程 | 一鍵端到端交付 |

### 典型工作流程

```
/plan                           # 1. Claude Code 規劃
/delegate P0                    # 2. 委派高優先任務給 Codex
/status                         # 3. 監控進度
/collect                        # 4. 收集並審查成果
/review-all                     # 5. 批次 review 所有 PR
/loop 30m /patrol               # 6. 設定持續巡邏
```

### Codex 配置

Plugin 安裝：
```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/codex:setup
```

建議的 `.codex/config.toml`：
```toml
model = "gpt-5.4-mini"
model_reasoning_effort = "high"
```

### 慣例

- 所有文件使用繁體中文，程式碼保留英文
- commit message 使用 conventional commits 格式
- 分支命名：`feature/<task-id>`、`fix/<task-id>`
- Codex 產出的 PR 加上 `codex-generated` label
- 文件產出到 `docs/` 目錄
- 追蹤記錄存放在 `docs/DELEGATION_LOG.md` 和 `docs/PATROL_LOG.md`

### 安全規則

以下變更不允許自動合併，必須人工確認：
- 環境變數 / 密鑰相關檔案
- CI/CD pipeline 配置
- 資料庫 migration
- 認證 / 授權模組
- 任何刪除超過 50 行的變更
