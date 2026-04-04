from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0090(**kwargs):
    import pandas as pd
    import requests
    from sqlalchemy import create_engine
    from utils.load_stage import (
        save_geodataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )
    from utils.transform_geometry import add_point_wkbgeometry_column_to_df
    from utils.transform_time import convert_str_to_time_format

    # Config
    dag_infos = kwargs.get("dag_infos")
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")

    # Taipei/New Taipei bounding box
    LAT_MIN, LAT_MAX = 24.7, 25.3
    LNG_MIN, LNG_MAX = 121.3, 122.0
    REALTIME_URL = "https://fhy.wra.gov.tw/WraApi/v1/Water/RealTimeInfo"
    STATION_URL = "https://fhy.wra.gov.tw/WraApi/v1/Water/Station"
    WARNING_URL = "https://fhy.wra.gov.tw/WraApi/v1/Water/Warning"
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    # Extract: station metadata (for coordinates)
    res_station = requests.get(STATION_URL, timeout=60)
    if res_station.status_code != 200:
        raise ValueError(f"Water Station API failed: {res_station.status_code}")
    stations = pd.DataFrame(res_station.json())

    # Filter stations within bounding box
    stations["Longitude"] = pd.to_numeric(stations["Longitude"], errors="coerce")
    stations["Latitude"] = pd.to_numeric(stations["Latitude"], errors="coerce")
    local_stations = stations[
        (stations["Latitude"] >= LAT_MIN)
        & (stations["Latitude"] <= LAT_MAX)
        & (stations["Longitude"] >= LNG_MIN)
        & (stations["Longitude"] <= LNG_MAX)
    ].copy()
    local_ids = set(local_stations["StationIdentifier"].tolist())

    if not local_ids:
        raise ValueError("No water level stations found in Taipei/New Taipei area")

    # Extract: real-time water level data
    res_realtime = requests.get(REALTIME_URL, timeout=60)
    if res_realtime.status_code != 200:
        raise ValueError(f"Water RealTimeInfo API failed: {res_realtime.status_code}")
    raw_realtime = pd.DataFrame(res_realtime.json())

    # Filter to local stations
    data = raw_realtime[
        raw_realtime["StationIdentifier"].isin(local_ids)
    ].reset_index(drop=True)

    if data.empty:
        raise ValueError("No real-time data for local water level stations")

    # Extract: warning thresholds
    res_warning = requests.get(WARNING_URL, timeout=60)
    warnings = pd.DataFrame()
    if res_warning.status_code == 200 and res_warning.json():
        warnings = pd.DataFrame(res_warning.json())

    # Merge station coordinates
    station_info = local_stations[
        ["StationIdentifier", "StationName", "Longitude", "Latitude", "BasinName"]
    ].copy()
    station_info = station_info.rename(columns={
        "StationName": "station_name_meta",
        "Longitude": "lng",
        "Latitude": "lat",
        "BasinName": "basin_name",
    })
    data = data.merge(station_info, on="StationIdentifier", how="left")

    # Merge warning thresholds if available
    if not warnings.empty:
        warning_info = warnings[
            ["StationIdentifier", "FloodWarningLevel"]
        ].drop_duplicates(subset=["StationIdentifier"])
        warning_info = warning_info.rename(columns={
            "FloodWarningLevel": "warning_level",
        })
        warning_info["warning_level"] = pd.to_numeric(
            warning_info["warning_level"], errors="coerce"
        )
        data = data.merge(warning_info, on="StationIdentifier", how="left")
    else:
        data["warning_level"] = None

    # Rename columns
    col_map = {
        "StationIdentifier": "station_id",
        "StationName": "station_name",
        "ObservationTime": "obs_time",
        "WaterLevel": "water_level",
    }
    data = data.rename(columns=col_map)

    # Use metadata station name if API name is missing
    if "station_name_meta" in data.columns:
        data["station_name"] = data["station_name"].fillna(data["station_name_meta"])
        data = data.drop(columns=["station_name_meta"])

    # Time conversion
    data["data_time"] = convert_str_to_time_format(
        data["obs_time"],
        from_format="%Y-%m-%dT%H:%M:%S",
    )

    # Convert water_level to numeric
    data["water_level"] = pd.to_numeric(data["water_level"], errors="coerce")

    # Compute alert_level: 0=normal, 1=advisory, 2=warning, 3=alert
    def compute_alert(row):
        wl = row.get("water_level")
        threshold = row.get("warning_level")
        if pd.isna(wl) or pd.isna(threshold):
            return 0
        if wl >= threshold:
            return 3
        elif wl >= threshold * 0.9:
            return 2
        elif wl >= threshold * 0.8:
            return 1
        return 0

    data["alert_level"] = data.apply(compute_alert, axis=1)

    # Add geometry
    data = add_point_wkbgeometry_column_to_df(
        data, data["lng"], data["lat"], from_crs=FROM_CRS
    )

    # Select output columns
    ready_data = data[[
        "data_time",
        "station_id",
        "station_name",
        "basin_name",
        "water_level",
        "warning_level",
        "alert_level",
        "lng",
        "lat",
        "wkb_geometry",
    ]]

    # Load
    engine = create_engine(ready_data_db_uri)
    save_geodataframe_to_postgresql(
        engine,
        gdata=ready_data,
        load_behavior=load_behavior,
        default_table=default_table,
        history_table=history_table,
        geometry_type=GEOMETRY_TYPE,
    )
    lasttime_in_data = data["data_time"].max()
    update_lasttime_in_data_to_dataset_info(engine, dag_id, lasttime_in_data)


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0090")
dag.create_dag(etl_func=_R0090)
