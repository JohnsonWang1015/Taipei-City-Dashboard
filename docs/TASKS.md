# 洪水防災儀表板 — 待辦任務清單

## 委派標準
- ✅ = 適合 Codex（獨立、有明確 spec、不涉及架構決策）
- ❌ = 需 Claude Code 處理（跨模組、需架構判斷）

## Phase 2: P1 防洪設施

### R0095 — F008 疏散門即時狀態 ✅
- **API**: `https://data.taipei/api/dataset/cc3f7e86-77ec-4bd3-a09f-05b175e192f5?scope=resourceAquire`
- **Table**: `taipei_floodgate_status` / `taipei_floodgate_status_history`
- **Schedule**: `*/10 * * * *`
- **Fields**: station_no, station_name, gate_total, gate_open, gate_close, data_time
- **Geometry**: No (station metadata separate)
- **Load**: `current+history`
- **Notes**: Response has `data` array with fields: stationNo, stationName, GateNum, recTime, foXX (開), fcXX (關). Count open/close gates per station.

### R0096 — F009 潮汐預報 ✅
- **API**: `https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0021-001?Authorization={CWA_API_KEY}`
- **Table**: `cwa_tidal_forecast`
- **Schedule**: `0 6 * * *` (daily 6AM)
- **Fields**: station_name, tide_time, tide_level, tide_type (high/low), data_time
- **Geometry**: Yes (station lat/lon in response)
- **Load**: `replace`
- **Notes**: CWA API key from Airflow Variable `CWA_API_KEY`. Filter to 淡水/基隆 stations. Response nested: records.TideForecasts[].Location[].TimePeriods.Daily[].Time[]

### R0097 — F010 土石流警戒 ✅
- **API**: `https://data.ardswc.gov.tw/Data/OpenData/Api`
- **Table**: `swcb_debris_flow_warning`
- **Schedule**: `0 */2 * * *` (every 2hr)
- **Fields**: stream_id, stream_name, alert_level, village, township, county, data_time
- **Geometry**: No (use separate shapefile for geometry)
- **Load**: `replace`
- **Notes**: Filter to 新北市 (county). API returns JSON array of warning statuses.

### R0098 — F011 新北抽水站 ✅
- **API**: `https://data.ntpc.gov.tw/api/datasets/3cdc5b9c-ce48-4dd6-8079-b9b3fa4b7296/json`
- **Table**: `ntpc_pump_station`
- **Schedule**: `0 4 * * *` (daily 4AM)
- **Fields**: station_name, address, river_system, completion_year, pump_type, data_time
- **Geometry**: No (address-based, geocode later)
- **Load**: `replace`
- **Notes**: 83 stations. Simple JSON array response. data.ntpc uses pagination with `page` and `size` params.

### R0099 — F012 新北水門 ✅
- **API**: `https://data.ntpc.gov.tw/api/datasets/{dataset_id}/json` (search "水門" on data.ntpc)
- **Table**: `ntpc_floodgate`
- **Schedule**: `0 4 * * *` (daily 4AM)
- **Fields**: gate_name, station_name, river_system, district, data_time
- **Geometry**: No
- **Load**: `replace`
- **Notes**: Similar pattern to R0098.

## Phase 3: P2 風險圖資

### R0100 — F014 歷史積水紀錄 ✅
- **API**: data.taipei KML download (歷史積水紀錄圖)
- **Table**: `taipei_historical_flood`
- **Schedule**: `0 3 1 1 *` (yearly Jan 1)
- **Fields**: location, district, date, depth, month, data_time
- **Geometry**: Yes (from KML points)
- **Load**: `replace`
- **Notes**: KML file needs geopandas/fiona to parse. Extract Placemark name/description/coordinates.

### R0101 — F015 易積水地區 ✅
- **API**: data.taipei KML + data.ntpc 十大低漥地區
- **Table**: `flood_prone_area`
- **Schedule**: `0 3 1 1 *` (yearly Jan 1)
- **Fields**: area_name, district, city, data_time
- **Geometry**: Yes (from KML polygons)
- **Load**: `replace`

### R0102 — F016 防災事件紀錄 ✅
- **API**: `https://fhy.wra.gov.tw/WraApi/v1/Event/Year/{Year}`
- **Table**: `wra_flood_events`
- **Schedule**: `0 4 1 * *` (monthly 1st)
- **Fields**: event_no, event_name, event_year, start_date, end_date, event_type, data_time
- **Geometry**: No
- **Load**: `replace`
- **Notes**: Iterate years from 2015 to current year. Simple JSON array.

## Phase 4: P3 疏散避難

### R0103 — F017 避難收容處所 ✅
- **APIs**: 
  - National: `https://data.gov.tw/dataset/73242` (JSON download)
  - Taipei: `https://data.taipei/api/dataset/aaf97773-3631-40e2-b3cc-da87bf2ce1d5?scope=resourceAquire`
  - New Taipei: `https://data.ntpc.gov.tw/api/datasets/25E439AB-49E7-4E5E-85CE-A25C13FD2770/json`
- **Table**: `evacuation_shelter`
- **Schedule**: `0 3 1 * *` (monthly 1st)
- **Fields**: shelter_name, address, capacity, district, city, lng, lat, data_time
- **Geometry**: Yes (from coordinates in response)
- **Load**: `replace`
- **Notes**: Merge 3 sources. Standardize column names. Some sources use TWD97, convert to WGS84.

### R0104 — F018 水利CCTV ✅
- **APIs**:
  - Taipei: `https://data.taipei/api/dataset/9dca148b-7ee3-422e-a53e-db70ab5b236a?scope=resourceAquire`
  - WRA: `https://data.gov.tw/dataset/36687` (JSON download)
- **Table**: `water_cctv_location`
- **Schedule**: `0 4 * * *` (daily 4AM)
- **Fields**: station_name, stream_url, source, lng, lat, data_time
- **Geometry**: Yes (for WRA; Taipei needs separate location dataset)
- **Load**: `replace`
- **Notes**: Taipei CCTV image URLs in response. WRA has coordinates. Merge both sources.
