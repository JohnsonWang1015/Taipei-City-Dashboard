from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0091(**kwargs):
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
    REALTIME_URL = "https://fhy.wra.gov.tw/WraApi/v1/Rain/RealTimeInfo"
    STATION_URL = "https://fhy.wra.gov.tw/WraApi/v1/Rain/Station"
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    # Extract: station metadata
    res_station = requests.get(STATION_URL, timeout=60)
    if res_station.status_code != 200:
        raise ValueError(f"Rain Station API failed: {res_station.status_code}")
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
        raise ValueError("No rain stations found in Taipei/New Taipei area")

    # Extract: real-time rainfall data
    res_realtime = requests.get(REALTIME_URL, timeout=60)
    if res_realtime.status_code != 200:
        raise ValueError(f"Rain RealTimeInfo API failed: {res_realtime.status_code}")
    raw_realtime = pd.DataFrame(res_realtime.json())

    # Filter to local stations
    data = raw_realtime[
        raw_realtime["StationIdentifier"].isin(local_ids)
    ].reset_index(drop=True)

    if data.empty:
        raise ValueError("No real-time data for local rain stations")

    # Merge station coordinates
    station_info = local_stations[
        ["StationIdentifier", "Longitude", "Latitude", "BasinName"]
    ].copy()
    station_info = station_info.rename(columns={
        "Longitude": "lng",
        "Latitude": "lat",
        "BasinName": "basin_name",
    })
    data = data.merge(station_info, on="StationIdentifier", how="left")

    # Rename columns
    col_map = {
        "StationIdentifier": "station_id",
        "StationName": "station_name",
        "ObservationTime": "obs_time",
        "Rainfall10Min": "rain_10min",
        "Rainfall1hr": "rain_1hr",
        "Rainfall3hr": "rain_3hr",
        "Rainfall6hr": "rain_6hr",
        "Rainfall12hr": "rain_12hr",
        "Rainfall24hr": "rain_24hr",
        "RainfallDaily": "rain_daily",
    }
    data = data.rename(columns=col_map)

    # Time conversion
    data["data_time"] = convert_str_to_time_format(
        data["obs_time"],
        from_format="%Y-%m-%dT%H:%M:%S",
    )

    # Convert numeric fields
    numeric_cols = [
        "rain_10min", "rain_1hr", "rain_3hr", "rain_6hr",
        "rain_12hr", "rain_24hr", "rain_daily",
    ]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

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
        "rain_10min",
        "rain_1hr",
        "rain_3hr",
        "rain_6hr",
        "rain_12hr",
        "rain_24hr",
        "rain_daily",
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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0091")
dag.create_dag(etl_func=_R0091)
