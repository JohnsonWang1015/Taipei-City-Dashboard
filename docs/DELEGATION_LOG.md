# Delegation Log — 洪水防災儀表板

## Codex 委派任務

| Task ID | 任務名稱 | 委派時間 | 狀態 | 審查結果 |
|---------|---------|---------|------|---------|
| R0095 | F008 疏散門即時狀態 | 2026-04-04 | collected | PASS |
| R0096 | F009 潮汐預報 | 2026-04-04 | collected | MINOR→fixed (空資料處理) |
| R0097 | F010 土石流警戒 | 2026-04-04 | collected | MINOR→fixed (logging) |
| R0098 | F011 新北抽水站 | 2026-04-04 | collected | PASS |
| R0099 | F012 新北水門 | 2026-04-04 | collected | MAJOR→rewritten (module-level constants) |
| R0100 | F014 歷史積水紀錄 | 2026-04-04 | collected | MAJOR→fixed (helpers moved inside ETL) |
| R0101 | F015 易積水地區 | 2026-04-04 | collected | MAJOR→fixed (constants + error handling) |
| R0102 | F016 防災事件紀錄 | 2026-04-04 | collected | PASS |
| R0103 | F017 避難收容處所 | 2026-04-04 | collected | MINOR (silent return on empty) |
| R0104 | F018 水利CCTV | 2026-04-04 | collected | MAJOR→fixed (module-level + placeholder guard) |

## Claude Code 直接實作

| Task ID | 任務名稱 | 完成時間 | 備註 |
|---------|---------|---------|------|
| R0090 | F001 河川水位即時監測 | 2026-04-04 | WRA Water API |
| R0091 | F002 即時雨量監測 | 2026-04-04 | WRA Rain API |
| R0092 | F003 台北市雨量站 | 2026-04-04 | data.taipei API |
| R0093 | F005 淹水感測器 | 2026-04-04 | Civil IoT SensorThings |
| R0094 | F007 水庫即時水情 | 2026-04-04 | WRA Reservoir API |

## 待解決 Placeholder URLs

| DAG | Placeholder | 需要確認的資料 |
|-----|-------------|---------------|
| R0099 | `PLACEHOLDER_NTPC_FLOODGATE_ID` | 新北市水門 dataset ID (data.ntpc.gov.tw) |
| R0100 | `PLACEHOLDER_HISTORICAL_FLOOD_KML_URL` | 台北歷史積水 KML 下載網址 (data.taipei) |
| R0101 | `PLACEHOLDER_FLOOD_PRONE_KML_URL` | 台北易積水地區 KML |
| R0101 | `PLACEHOLDER_NTPC_LOWLYING_URL` | 新北十大低漥地區 API |
| R0103 | `PLACEHOLDER_NATIONAL_SHELTER_URL` | 全國避難處所 JSON 下載網址 |
| R0104 | `PLACEHOLDER` (CCTV location) | 台北 CCTV 座標 dataset |
| R0104 | `PLACEHOLDER_WRA_CCTV_URL` | 水利署 CCTV JSON 下載網址 |
