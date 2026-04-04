--
-- Flood Disaster Prevention Dashboard Seed Data
-- 洪水防災儀表板 種子資料
--
-- Component IDs: 300-317
-- Component Map IDs: 200-220
-- Dashboard IDs: 400-403
--

-- ============================================================
-- 1. COMPONENTS (18 components)
-- ============================================================

INSERT INTO components (id, index, name) VALUES
(300, 'river_water_level', '河川水位即時監測'),
(301, 'realtime_rainfall', '即時雨量監測'),
(302, 'taipei_rainfall_station', '台北市雨量站'),
(303, 'sewer_water_level', '下水道水位監測'),
(304, 'flood_sensor', '淹水感測器'),
(305, 'pump_station_status', '抽水站運作動態'),
(306, 'reservoir_realtime', '水庫即時水情'),
(307, 'floodgate_status', '疏散門/閘門狀態'),
(308, 'tidal_forecast', '潮汐預報'),
(309, 'debris_flow_warning', '土石流警戒'),
(310, 'ntpc_pump_station', '新北抽水站'),
(311, 'ntpc_floodgate', '新北水門'),
(312, 'flood_inundation_potential', '淹水潛勢圖'),
(313, 'historical_flood_record', '歷史積水紀錄'),
(314, 'flood_prone_area', '易積水地區'),
(315, 'flood_event_timeline', '防災事件紀錄'),
(316, 'evacuation_shelter', '避難收容處所'),
(317, 'water_cctv', '水利CCTV即時影像');

-- ============================================================
-- 2. COMPONENT CHARTS
-- ============================================================

INSERT INTO component_charts (index, color, types, unit) VALUES
-- Dashboard 1: 洪水即時監測
('river_water_level',    '{#4CAF50,#FFC107,#FF9800,#F44336}', '{GuageChart,TimelineSeparateChart}', '公尺'),
('realtime_rainfall',    '{#E3F2FD,#80DEEA,#26C6DA,#00ACC1,#FF8F00,#D50000}', '{ColumnChart,TimelineSeparateChart}', '毫米'),
('taipei_rainfall_station', '{#039BE5,#0277BD,#01579B}', '{BarChart,TimelineSeparateChart}', '毫米'),
('sewer_water_level',    '{#4CAF50,#FFC107,#FF9800,#F44336}', '{GuageChart,TimelineSeparateChart}', '公尺'),
('flood_sensor',         '{#1565C0,#F44336}', '{TextUnitChart,MapLegend}', '處'),
('pump_station_status',  '{#4CAF50,#F44336,#9E9E9E}', '{DonutChart,MapLegend}', '站'),
('reservoir_realtime',   '{#1E88E5,#42A5F5,#90CAF9}', '{GuageChart,BarPercentChart}', '%'),
-- Dashboard 2: 防洪設施
('floodgate_status',     '{#4CAF50,#F44336}', '{DonutChart,BarChart}', '座'),
('tidal_forecast',       '{#0277BD,#4FC3F7}', '{TimelineSeparateChart}', '公分'),
('debris_flow_warning',  '{#FFC107,#F44336}', '{TextUnitChart,MapLegend}', '條'),
('ntpc_pump_station',    '{#26A69A,#80CBC4}', '{BarChart,MapLegend}', '站'),
('ntpc_floodgate',       '{#5C6BC0,#7986CB}', '{MapLegend}', '座'),
-- Dashboard 3: 風險圖資
('flood_inundation_potential', '{#E3F2FD,#90CAF9,#42A5F5,#1E88E5,#1565C0,#0D47A1}', '{MapLegend}', '公尺'),
('historical_flood_record',   '{#BBDEFB,#64B5F6,#1E88E5,#0D47A1}', '{HeatmapChart,ColumnChart}', '次'),
('flood_prone_area',     '{#FFCC80,#FF9800,#E65100}', '{BarChart,MapLegend}', '處'),
('flood_event_timeline', '{#1565C0,#0D47A1}', '{ColumnChart,TimelineSeparateChart}', '件'),
-- Dashboard 4: 疏散避難
('evacuation_shelter',   '{#66BB6A,#43A047}', '{BarChart,MapLegend}', '處'),
('water_cctv',           '{#78909C,#546E7A}', '{MapLegend}', '台');

-- ============================================================
-- 3. COMPONENT MAPS
-- ============================================================

INSERT INTO component_maps (id, index, title, type, source, size, icon, paint, property) VALUES
-- F001 河川水位
(200, 'river_water_level', '河川水位站', 'circle', 'geojson', NULL, NULL,
 '{"circle-color":["step",["get","alert_level"],"#4CAF50",1,"#FFC107",2,"#FF9800",3,"#F44336"],"circle-radius":["interpolate",["linear"],["zoom"],10,4,14,8],"circle-opacity":0.85}',
 '[{"key":"station_name","name":"測站名稱"},{"key":"water_level","name":"水位(m)"},{"key":"alert_level","name":"警戒等級"},{"key":"warning_level","name":"警戒水位(m)"},{"key":"data_time","name":"觀測時間"}]'),
-- F002 即時雨量
(201, 'realtime_rainfall', '雨量站', 'circle', 'geojson', NULL, NULL,
 '{"circle-color":["step",["get","rain_10min"],"#E0F7FA",1,"#80DEEA",10,"#26C6DA",30,"#00ACC1",50,"#FF8F00",80,"#D50000"],"circle-radius":["interpolate",["linear"],["zoom"],10,4,14,8],"circle-opacity":0.85}',
 '[{"key":"station_name","name":"測站名稱"},{"key":"rain_10min","name":"10分鐘雨量(mm)"},{"key":"rain_1hr","name":"1小時雨量(mm)"},{"key":"rain_24hr","name":"24小時雨量(mm)"},{"key":"data_time","name":"觀測時間"}]'),
-- F003 台北市雨量站
(202, 'taipei_rainfall_station', '台北市雨量站', 'circle', 'geojson', NULL, NULL,
 '{"circle-color":["step",["get","rain_daily"],"#E0F7FA",1,"#80DEEA",10,"#26C6DA",30,"#00ACC1",50,"#FF8F00",80,"#D50000"],"circle-radius":["interpolate",["linear"],["zoom"],10,4,14,8],"circle-opacity":0.85}',
 '[{"key":"station_name","name":"測站名稱"},{"key":"rain_daily","name":"日累積雨量(mm)"},{"key":"data_time","name":"觀測時間"}]'),
-- F004 下水道水位
(203, 'sewer_water_level', '下水道水位站', 'circle', 'geojson', NULL, NULL,
 '{"circle-color":["step",["get","ground_far"],"#F44336",0,"#F44336",0.5,"#FF9800",1.0,"#FFC107",2.0,"#4CAF50"],"circle-radius":["interpolate",["linear"],["zoom"],10,3,14,7],"circle-opacity":0.85}',
 '[{"key":"station_name","name":"測站名稱"},{"key":"level_out","name":"外水位(m)"},{"key":"ground_far","name":"離地高(m)"},{"key":"district","name":"行政區"},{"key":"data_time","name":"觀測時間"}]'),
-- F005 淹水感測器
(204, 'flood_sensor', '淹水感測器', 'circle', 'geojson', NULL, NULL,
 '{"circle-color":["step",["get","water_depth"],"#4CAF50",0,"#4CAF50",0.01,"#FFC107",0.1,"#FF9800",0.3,"#F44336"],"circle-radius":["interpolate",["linear"],["zoom"],10,4,14,8],"circle-opacity":0.85}',
 '[{"key":"station_name","name":"感測器名稱"},{"key":"water_depth","name":"積水深度(m)"},{"key":"data_time","name":"觀測時間"}]'),
-- F006 抽水站
(205, 'pump_station_status', '抽水站', 'symbol', 'geojson', NULL, 'pump',
 '{}',
 '[{"key":"station_name","name":"站名"},{"key":"all_pumb_lights","name":"運轉狀態"},{"key":"pumb_num","name":"抽水機數"},{"key":"door_num","name":"閘門數"},{"key":"rec_time","name":"更新時間"}]'),
-- F007 水庫
(206, 'reservoir_realtime', '水庫', 'symbol', 'geojson', NULL, 'reservoir',
 '{}',
 '[{"key":"reservoir_name","name":"水庫名稱"},{"key":"water_level","name":"水位(m)"},{"key":"storage_percent","name":"蓄水率(%)"},{"key":"inflow","name":"進水量(cms)"},{"key":"outflow","name":"放水量(cms)"},{"key":"data_time","name":"觀測時間"}]'),
-- F008 疏散門
(207, 'floodgate_status', '疏散門', 'symbol', 'geojson', NULL, 'floodgate',
 '{}',
 '[{"key":"station_name","name":"站名"},{"key":"gate_open","name":"開啟數"},{"key":"gate_close","name":"關閉數"},{"key":"gate_total","name":"閘門總數"},{"key":"data_time","name":"更新時間"}]'),
-- F010 土石流
(208, 'debris_flow_warning', '土石流潛勢溪流', 'fill', 'geojson', NULL, NULL,
 '{"fill-color":["match",["get","alert_level"],"紅色警戒","#F44336","黃色警戒","#FFC107","#9E9E9E"],"fill-opacity":0.5}',
 '[{"key":"stream_name","name":"溪流名稱"},{"key":"alert_level","name":"警戒等級"},{"key":"village","name":"影響村里"}]'),
-- F011 新北抽水站
(209, 'ntpc_pump_station', '新北抽水站', 'symbol', 'geojson', NULL, 'pump',
 '{}',
 '[{"key":"station_name","name":"站名"},{"key":"address","name":"地址"},{"key":"river_system","name":"水系"}]'),
-- F012 新北水門
(210, 'ntpc_floodgate', '新北水門', 'symbol', 'geojson', NULL, 'floodgate',
 '{}',
 '[{"key":"gate_name","name":"水門名稱"},{"key":"station_name","name":"抽水站"},{"key":"river_system","name":"水系"},{"key":"district","name":"行政區"}]'),
-- F013 淹水潛勢圖 (3 layers matching existing GeoJSON files)
(211, 'flood_simulate_78', '淹水潛勢(78.8mm)', 'fill', 'geojson', NULL, NULL,
 '{"fill-color":"#90CAF9","fill-opacity":0.4}',
 '[{"key":"gridcode","name":"淹水等級"}]'),
(216, 'flood_simulate_100', '淹水潛勢(100mm)', 'fill', 'geojson', NULL, NULL,
 '{"fill-color":"#42A5F5","fill-opacity":0.4}',
 '[{"key":"gridcode","name":"淹水等級"}]'),
(217, 'flood_simulate_130', '淹水潛勢(130mm)', 'fill', 'geojson', NULL, NULL,
 '{"fill-color":"#1565C0","fill-opacity":0.4}',
 '[{"key":"gridcode","name":"淹水等級"}]'),
-- F014 歷史積水紀錄
(212, 'historical_flood_record', '歷史積水點', 'circle', 'geojson', NULL, NULL,
 '{"circle-color":"#1565C0","circle-radius":5,"circle-opacity":0.7}',
 '[{"key":"location","name":"積水地點"},{"key":"date","name":"發生日期"},{"key":"depth","name":"積水深度"}]'),
-- F015 易積水地區
(213, 'flood_prone_area', '易積水地區', 'fill', 'geojson', NULL, NULL,
 '{"fill-color":"#FF9800","fill-opacity":0.4,"fill-outline-color":"#E65100"}',
 '[{"key":"area_name","name":"地區名稱"},{"key":"district","name":"行政區"}]'),
-- F017 避難處所
(214, 'evacuation_shelter', '避難收容處所', 'symbol', 'geojson', NULL, 'shelter',
 '{}',
 '[{"key":"shelter_name","name":"場所名稱"},{"key":"address","name":"地址"},{"key":"capacity","name":"容納人數"},{"key":"district","name":"行政區"}]'),
-- F018 CCTV
(215, 'water_cctv', '水利CCTV', 'symbol', 'geojson', NULL, 'cctv',
 '{}',
 '[{"key":"station_name","name":"站名"},{"key":"stream_url","name":"即時影像"},{"key":"source","name":"來源"}]');

-- ============================================================
-- 4. QUERY CHARTS (taipei + metrotaipei entries)
-- ============================================================

-- F001 河川水位即時監測 (metrotaipei = both cities)
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('river_water_level', NULL, '{200}', NULL, 'current', NULL, 10, 'minute',
 '經濟部水利署',
 '顯示台北市與新北市河川水位即時監測資料，依警戒等級以不同顏色呈現。',
 '本元件整合經濟部水利署即時水位資料與警戒門檻值，顯示雙北地區河川水位站的即時水位、警戒等級。資料每10分鐘更新一次。警戒等級分為：正常（綠色）、二級警戒（黃色）、一級警戒（橙色）、特報（紅色）。',
 '汛期間即時監控河川水位變化，當水位接近或超過警戒值時，可提前啟動防洪應變措施。搭配地圖模式可快速辨識高風險測站位置。',
 '{https://fhy.wra.gov.tw/WraApi/v1/Water/RealTimeInfo}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'time',
 'SELECT data_time as x_axis, station_name as y_axis, water_level as data FROM wra_river_water_level ORDER BY data_time',
 'SELECT DATE_TRUNC(%s, data_time) as x_axis, station_name as y_axis, AVG(water_level) as data FROM wra_river_water_level_history WHERE data_time BETWEEN %s AND %s GROUP BY 1, 2 ORDER BY 1',
 'metrotaipei');

-- F002 即時雨量監測
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('realtime_rainfall', NULL, '{201}', NULL, 'current', NULL, 10, 'minute',
 '經濟部水利署',
 '顯示雙北地區即時雨量監測資料。',
 '整合水利署雨量站資料，呈現各站10分鐘、1小時、24小時累積雨量。依雨量大小以色階呈現，資料每10分鐘更新。',
 '即時掌握降雨分布與強度，作為啟動防洪整備及疏散判斷的依據。',
 '{https://fhy.wra.gov.tw/WraApi/v1/Rain/RealTimeInfo}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'time',
 'SELECT data_time as x_axis, station_name as y_axis, rain_1hr as data FROM wra_rainfall_realtime ORDER BY data_time',
 'SELECT DATE_TRUNC(%s, data_time) as x_axis, station_name as y_axis, MAX(rain_1hr) as data FROM wra_rainfall_realtime_history WHERE data_time BETWEEN %s AND %s GROUP BY 1, 2 ORDER BY 1',
 'metrotaipei');

-- F003 台北市雨量站
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('taipei_rainfall_station', NULL, '{202}', NULL, 'current', NULL, 10, 'minute',
 '台北市工務局水利處',
 '顯示台北市42座雨量站即時雨量資料。',
 '台北市工務局水利處設置之42座雨量站即時資料，提供比中央雨量站更密集的市區降雨監測。資料每10分鐘更新。',
 '針對台北市區提供更精確的降雨分布資訊，輔助市區排水系統監控。',
 '{https://data.taipei/dataset/detail?id=6f03a0b8-7b98-4eea-8bb9-ba6bfcdc2b8b}', '{doit}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'two_d',
 'SELECT station_name as x_axis, rain_daily as data FROM taipei_rainfall_station ORDER BY rain_daily DESC',
 NULL,
 'taipei');

-- F004 下水道水位 (reuses R0034)
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('sewer_water_level', NULL, '{203}', NULL, 'current', NULL, 5, 'minute',
 '台北市工務局水利處',
 '顯示台北市下水道水位即時監測資料，依離地高度以色階呈現。',
 '台北市工務局水利處設置之214座雨水下水道水位監測站即時資料。離地高度（ground_far）越小代表水位越高、越危險。',
 '即時監控下水道排水情形，當離地高度過低時可預警區域淹水風險。',
 '{https://data.taipei/dataset/detail?id=b3648c5d-15c8-416a-a603-fda7a9ac1b0d}', '{doit}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'time',
 'SELECT data_time as x_axis, station_name as y_axis, ground_far as data FROM patrol_rain_sewer ORDER BY data_time',
 'SELECT DATE_TRUNC(%s, data_time) as x_axis, station_name as y_axis, AVG(ground_far) as data FROM patrol_rain_sewer_history WHERE data_time BETWEEN %s AND %s GROUP BY 1, 2 ORDER BY 1',
 'taipei');

-- F005 淹水感測器
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('flood_sensor', NULL, '{204}', NULL, 'current', NULL, 10, 'minute',
 '民生公共物聯網',
 '顯示雙北地區淹水感測器即時資料。',
 '整合民生公共物聯網淹水感測器資料，即時顯示各感測點的積水深度。無積水顯示為綠色，有積水依深度從黃色到紅色。',
 '即時偵測路面積水狀況，提供淹水預警與災情回報的佐證。',
 '{https://sta.colife.org.tw/STA_FloodSensor/v1.0/Things}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'map_legend',
 'SELECT station_name as name, ''circle'' as type, NULL as icon, water_depth as value FROM colife_flood_sensor ORDER BY water_depth DESC',
 NULL,
 'metrotaipei');

-- F006 抽水站運作動態 (reuses R0036)
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('pump_station_status', NULL, '{205}', NULL, 'current', NULL, 5, 'minute',
 '台北市工務局水利處',
 '顯示台北市抽水站即時運轉狀態。',
 '台北市抽水站即時運轉狀態，顯示各站抽水機運轉中/停止的比例。資料每5分鐘更新。',
 '即時掌握抽水站運作情形，確保防洪排水能力正常。',
 '{https://data.taipei/dataset/detail?id=2bbfb30e-de58-43bd-9cc9-b56e9a6b5369}', '{doit}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'two_d',
 'SELECT all_pumb_lights as x_axis, COUNT(*) as data FROM patrol_rain_floodgate GROUP BY all_pumb_lights',
 NULL,
 'taipei');

-- F007 水庫即時水情
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('reservoir_realtime', NULL, '{206}', NULL, 'current', NULL, 30, 'minute',
 '經濟部水利署',
 '顯示供應雙北用水的水庫即時水情。',
 '整合水利署水庫即時資料，顯示翡翠水庫與石門水庫的蓄水率、水位、進出水量等資訊。資料每30分鐘更新。',
 '監控水庫蓄水量及洩洪情形，蓄水率過高時需注意洩洪對下游河川水位的影響。',
 '{https://fhy.wra.gov.tw/WraApi/v1/Reservoir/RealTimeInfo}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'percent',
 'SELECT reservoir_name as x_axis, ''蓄水率'' as y_axis, storage_percent as data FROM wra_reservoir_realtime',
 'SELECT DATE_TRUNC(%s, data_time) as x_axis, reservoir_name as y_axis, AVG(storage_percent) as data FROM wra_reservoir_realtime_history WHERE data_time BETWEEN %s AND %s GROUP BY 1, 2 ORDER BY 1',
 'metrotaipei');

-- F008 疏散門狀態
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('floodgate_status', NULL, '{207}', NULL, 'current', NULL, 10, 'minute',
 '台北市工務局水利處',
 '顯示台北市疏散門即時啟閉狀態。',
 '台北市疏散門即時監控資料，顯示各閘門的開啟/關閉狀態。颱風或大雨期間閘門關閉以防止河水倒灌。資料每10分鐘更新。',
 '即時掌握疏散門啟閉狀態，確保防洪閘門運作正常。',
 '{https://data.taipei/dataset/detail?id=cc3f7e86-77ec-4bd3-a09f-05b175e192f5}', '{doit}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'two_d',
 'SELECT ''開啟'' as x_axis, SUM(gate_open) as data FROM taipei_floodgate_status UNION ALL SELECT ''關閉'' as x_axis, SUM(gate_close) as data FROM taipei_floodgate_status',
 NULL,
 'taipei');

-- F009 潮汐預報
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('tidal_forecast', NULL, '{}', NULL, 'current', NULL, 1, 'day',
 '中央氣象署',
 '顯示淡水河口潮汐預報資料。',
 '中央氣象署潮汐預報資料，顯示淡水/基隆等河口站點未來48小時的潮位預測。潮汐加上暴雨會加劇河川水位上漲。',
 '研判複合型洪災風險，當大潮與豪雨重疊時需提高防洪警戒。',
 '{https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0021-001}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'time',
 'SELECT tide_time as x_axis, station_name as y_axis, tide_level as data FROM cwa_tidal_forecast WHERE tide_time >= NOW() ORDER BY tide_time',
 NULL,
 'metrotaipei');

-- F010 土石流警戒
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('debris_flow_warning', NULL, '{208}', NULL, 'current', NULL, 2, 'hour',
 '農業部水土保持署',
 '顯示雙北地區土石流潛勢溪流警戒狀態。',
 '水土保持署土石流防災資訊，顯示紅色/黃色警戒溪流。主要影響新北市山區（新店、烏來、深坑等）。每2小時更新。',
 '山區豪雨期間監控土石流警戒，協助撤離決策。',
 '{https://data.ardswc.gov.tw/Data/OpenData/Api}', '{ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'map_legend',
 'SELECT stream_name as name, ''fill'' as type, NULL as icon, alert_level as value FROM swcb_debris_flow_warning WHERE alert_level IS NOT NULL',
 NULL,
 'metrotaipei');

-- F011 新北抽水站
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('ntpc_pump_station', NULL, '{209}', NULL, 'current', NULL, 1, 'day',
 '新北市水利局',
 '顯示新北市抽水站分布與基本資訊。',
 '新北市水利局轄管之83座抽水站位置與基本資訊，包含水系、地址等。',
 '了解新北市防洪排水設施分布，作為災防整備參考。',
 '{https://data.ntpc.gov.tw/datasets/3cdc5b9c-ce48-4dd6-8079-b9b3fa4b7296}', '{ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'two_d',
 'SELECT river_system as x_axis, COUNT(*) as data FROM ntpc_pump_station GROUP BY river_system ORDER BY data DESC',
 NULL,
 'metrotaipei');

-- F012 新北水門
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('ntpc_floodgate', NULL, '{210}', NULL, 'current', NULL, 1, 'day',
 '新北市水利局',
 '顯示新北市水門分布資訊。',
 '新北市水利局轄管之水門位置與基本資訊。',
 '了解新北市水門設施分布。',
 '{https://data.ntpc.gov.tw}', '{ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'map_legend',
 'SELECT gate_name as name, ''symbol'' as type, NULL as icon, district as value FROM ntpc_floodgate',
 NULL,
 'metrotaipei');

-- F013 淹水潛勢圖 (reuses existing rainfall_flood_simulation_etl)
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('flood_inundation_potential', NULL, '{211,216,217}', NULL, 'static', NULL, 0, NULL,
 '國家災害防救科技中心',
 '顯示雙北地區不同降雨情境下的淹水潛勢分布。',
 '國家災害防救科技中心(NCDR)提供之淹水潛勢圖資，涵蓋78.8mm、100mm、130mm三種降雨情境的模擬淹水深度。',
 '汛期前瞭解淹水高風險地區，作為防災整備與疏散路線規劃依據。',
 '{https://dmap.ncdr.nat.gov.tw/}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'map_legend',
 'SELECT scenario as name, ''fill'' as type, NULL as icon, area_km2 as value FROM rainfall_flood_simulation_summary',
 NULL,
 'metrotaipei');

-- F014 歷史積水紀錄
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('historical_flood_record', NULL, '{212}', NULL, 'static', NULL, 0, NULL,
 '台北市工務局水利處',
 '顯示台北市歷年積水紀錄統計。',
 '台北市歷年積水事件紀錄，呈現各行政區、各月份的積水次數分布。',
 '分析歷史積水熱點與季節趨勢，輔助防洪設施優先改善決策。',
 '{https://data.taipei}', '{doit}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'three_d',
 'SELECT district as x_axis, month as y_axis, COUNT(*) as data FROM taipei_historical_flood GROUP BY district, month ORDER BY district, month',
 NULL,
 'taipei');

-- F015 易積水地區
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('flood_prone_area', NULL, '{213}', NULL, 'static', NULL, 0, NULL,
 '台北市工務局水利處 / 新北市水利局',
 '顯示雙北地區已知易積水地區。',
 '台北市易積水地區與新北市十大低漥地區資料，標示已知的積水風險區域。',
 '事前了解易積水地區位置，作為防災準備與交通管制參考。',
 '{https://data.taipei,https://data.ntpc.gov.tw}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'two_d',
 'SELECT district as x_axis, COUNT(*) as data FROM flood_prone_area GROUP BY district ORDER BY data DESC',
 NULL,
 'metrotaipei');

-- F016 防災事件紀錄
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('flood_event_timeline', NULL, '{}', NULL, 'static', NULL, 1, 'month',
 '經濟部水利署',
 '顯示歷年水利署防災事件紀錄。',
 '水利署防災事件資料，記錄歷年颱風、豪雨等水災事件。',
 '回顧歷年防災事件，作為防災經驗傳承參考。',
 '{https://fhy.wra.gov.tw/WraApi/v1/Event}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'two_d',
 'SELECT event_year as x_axis, COUNT(*) as data FROM wra_flood_events GROUP BY event_year ORDER BY event_year',
 NULL,
 'metrotaipei');

-- F017 避難收容處所
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('evacuation_shelter', NULL, '{214}', NULL, 'static', NULL, 1, 'month',
 '內政部消防署 / 台北市 / 新北市',
 '顯示雙北地區避難收容處所分布。',
 '整合中央、台北市、新北市三級政府避難收容處所資料，包含場所名稱、地址、容納人數等資訊。',
 '災害發生時引導民眾前往最近的避難處所，並掌握各處所容納量。',
 '{https://data.gov.tw/dataset/73242,https://data.taipei,https://data.ntpc.gov.tw}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'two_d',
 'SELECT district as x_axis, COUNT(*) as data FROM evacuation_shelter GROUP BY district ORDER BY data DESC',
 NULL,
 'metrotaipei');

-- F018 水利CCTV
INSERT INTO query_charts (index, history_config, map_config_ids, map_filter, time_from, time_to, update_freq, update_freq_unit, source, short_desc, long_desc, use_case, links, contributors, created_at, updated_at, query_type, query_chart, query_history, city) VALUES
('water_cctv', NULL, '{215}', NULL, 'current', NULL, 1, 'day',
 '台北市工務局水利處 / 經濟部水利署',
 '顯示雙北水利相關CCTV監視器位置。',
 '整合台北市水利處156台與水利署全國CCTV影像站位置資料。點擊地圖標記可查看即時影像連結。',
 '遠端監控河川、排水設施現場狀況，輔助災情研判。',
 '{https://data.taipei/dataset/detail?id=9dca148b-7ee3-422e-a53e-db70ab5b236a,https://data.gov.tw/dataset/36687}', '{doit,ntpc}',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
 'map_legend',
 'SELECT station_name as name, ''symbol'' as type, stream_url as icon, source as value FROM water_cctv_location',
 NULL,
 'metrotaipei');

-- ============================================================
-- 5. DASHBOARDS (4 dashboards)
-- ============================================================

INSERT INTO dashboards (id, index, name, components, icon, updated_at, created_at) VALUES
(400, 'flood_monitoring',      '洪水即時監測', '{300,301,302,303,304,305,306}', 'water_drop',   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(401, 'flood_infrastructure',  '防洪設施',     '{305,307,308,309,310,311}',     'engineering',  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(402, 'flood_risk',            '風險圖資',     '{312,313,314,315}',             'map',          CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(403, 'flood_evacuation',      '疏散避難',     '{316,317}',                     'emergency',    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- ============================================================
-- 6. DASHBOARD GROUPS (visibility)
-- ============================================================

-- group 1=public, 2=taipei, 3=metrotaipei
INSERT INTO dashboard_groups (dashboard_id, group_id) VALUES
(400, 2), (400, 3),  -- 洪水即時監測: both cities
(401, 2), (401, 3),  -- 防洪設施: both cities
(402, 2), (402, 3),  -- 風險圖資: both cities
(403, 2), (403, 3);  -- 疏散避難: both cities

-- ============================================================
-- 7. SEQUENCES (reset auto-increment to avoid conflicts)
-- ============================================================

SELECT setval('components_id_seq', (SELECT MAX(id) FROM components));
SELECT setval('component_maps_id_seq', (SELECT MAX(id) FROM component_maps));
SELECT setval('dashboards_id_seq', (SELECT MAX(id) FROM dashboards));
