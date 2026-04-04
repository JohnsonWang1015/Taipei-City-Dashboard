from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0093(**kwargs):
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
    BASE_URL = "https://sta.colife.org.tw/STA_FloodSensor/v1.0/Things"
    EXPAND = "$expand=Locations,Datastreams/Observations($top=1;$orderby=phenomenonTime desc)"
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    # Extract: paginate through SensorThings API
    all_things = []
    url = f"{BASE_URL}?{EXPAND}&$top=100"
    while url:
        res = requests.get(url, timeout=120)
        if res.status_code != 200:
            raise ValueError(f"Civil IoT FloodSensor API failed: {res.status_code}")
        result = res.json()
        things = result.get("value", [])
        all_things.extend(things)
        url = result.get("@iot.nextLink", None)

    if not all_things:
        raise ValueError("No flood sensor data from Civil IoT")

    # Transform: extract sensor data with coordinates and latest observation
    records = []
    for thing in all_things:
        # Extract location
        locations = thing.get("Locations", [])
        if not locations:
            continue
        loc = locations[0].get("location", {})
        coords = loc.get("coordinates", [])
        if not coords or len(coords) < 2:
            continue

        lng, lat = coords[0], coords[1]

        # Filter to Taipei/New Taipei bounding box
        if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
            continue

        # Extract latest observation from first datastream
        water_depth = None
        obs_time = None
        datastreams = thing.get("Datastreams", [])
        for ds in datastreams:
            observations = ds.get("Observations", [])
            if observations:
                obs = observations[0]
                water_depth = obs.get("result")
                obs_time = obs.get("phenomenonTime")
                break

        records.append({
            "thing_id": thing.get("@iot.id"),
            "station_name": thing.get("name", ""),
            "description": thing.get("description", ""),
            "lng": lng,
            "lat": lat,
            "water_depth": water_depth,
            "obs_time": obs_time,
        })

    if not records:
        raise ValueError("No flood sensors found in Taipei/New Taipei area")

    data = pd.DataFrame(records)

    # Convert types
    data["water_depth"] = pd.to_numeric(data["water_depth"], errors="coerce").fillna(0)

    # Time conversion
    if data["obs_time"].notna().any():
        data["data_time"] = convert_str_to_time_format(
            data["obs_time"],
            from_format="%Y-%m-%dT%H:%M:%S",
            is_from_utc=True,
        )
    else:
        data["data_time"] = pd.Timestamp.now(tz="Asia/Taipei")

    # Add geometry
    data = add_point_wkbgeometry_column_to_df(
        data, data["lng"], data["lat"], from_crs=FROM_CRS
    )

    # Select output columns
    ready_data = data[[
        "data_time",
        "thing_id",
        "station_name",
        "water_depth",
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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0093")
dag.create_dag(etl_func=_R0093)
