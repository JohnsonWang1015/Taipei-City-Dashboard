from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0094(**kwargs):
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

    # Target reservoirs serving Taipei metro area
    TARGET_RESERVOIRS = ["翡翠水庫", "石門水庫"]
    REALTIME_URL = "https://fhy.wra.gov.tw/WraApi/v1/Reservoir/RealTimeInfo"
    STATION_URL = "https://fhy.wra.gov.tw/WraApi/v1/Reservoir/Station"
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    # Extract: real-time data
    res = requests.get(REALTIME_URL, timeout=60)
    if res.status_code != 200:
        raise ValueError(f"Reservoir RealTimeInfo API failed: {res.status_code}")
    raw_realtime = pd.DataFrame(res.json())

    # Extract: station metadata (for coordinates)
    res_station = requests.get(STATION_URL, timeout=60)
    if res_station.status_code != 200:
        raise ValueError(f"Reservoir Station API failed: {res_station.status_code}")
    raw_station = pd.DataFrame(res_station.json())

    # Transform: filter target reservoirs
    data = raw_realtime.copy()
    data = data[data["ReservoirName"].isin(TARGET_RESERVOIRS)].reset_index(drop=True)
    if data.empty:
        raise ValueError(f"No data for target reservoirs: {TARGET_RESERVOIRS}")

    # Merge station coordinates
    station_coords = raw_station[["ReservoirIdentifier", "Longitude", "Latitude"]].copy()
    data = data.merge(
        station_coords,
        on="ReservoirIdentifier",
        how="left",
    )

    # Rename columns
    col_map = {
        "ReservoirIdentifier": "reservoir_id",
        "ReservoirName": "reservoir_name",
        "ObservationTime": "obs_time",
        "EffectiveWaterStorageCapacity": "effective_capacity",
        "WaterLevel": "water_level",
        "EffectiveStorage": "effective_storage",
        "StoragePercentage": "storage_percent",
        "Inflow": "inflow",
        "Outflow": "outflow",
        "CatchmentAreaRainfall": "catchment_rainfall",
        "Longitude": "lng",
        "Latitude": "lat",
    }
    data = data.rename(columns=col_map)

    # Time conversion
    data["data_time"] = convert_str_to_time_format(
        data["obs_time"],
        from_format="%Y-%m-%dT%H:%M:%S",
    )

    # Convert numeric fields
    numeric_cols = [
        "water_level", "effective_storage", "storage_percent",
        "inflow", "outflow", "catchment_rainfall", "effective_capacity",
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
        "reservoir_id",
        "reservoir_name",
        "water_level",
        "effective_capacity",
        "effective_storage",
        "storage_percent",
        "inflow",
        "outflow",
        "catchment_rainfall",
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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0094")
dag.create_dag(etl_func=_R0094)
