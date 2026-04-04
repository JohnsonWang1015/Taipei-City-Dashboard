from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0096(**kwargs):
    import pandas as pd
    import requests
    from airflow.models import Variable
    from sqlalchemy import create_engine
    from utils.load_stage import (
        save_geodataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )
    from utils.transform_geometry import add_point_wkbgeometry_column_to_df

    # Config
    cwa_api_key = Variable.get("CWA_API_KEY")
    dag_infos = kwargs.get("dag_infos")
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")
    URL = (
        "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0021-001"
        f"?Authorization={cwa_api_key}"
    )
    TARGET_KEYWORDS = ["淡水", "基隆", "台北"]
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    # Extract
    res = requests.get(URL, timeout=60)
    res.raise_for_status()
    raw_data = res.json()

    # Transform
    rows = []
    locations = raw_data["records"]["TideForecasts"][0]["Location"]
    for loc in locations:
        station_name = loc["LocationName"]
        if not any(keyword in station_name for keyword in TARGET_KEYWORDS):
            continue

        station_id = loc.get("StationID", "")
        lat = pd.to_numeric(loc.get("Latitude"), errors="coerce")
        lng = pd.to_numeric(loc.get("Longitude"), errors="coerce")
        if pd.isna(lat) or pd.isna(lng):
            continue

        for daily in loc["TimePeriods"]["Daily"]:
            data_time = daily["Date"]
            for item in daily["Time"]:
                rows.append(
                    {
                        "station_name": station_name,
                        "station_id": station_id,
                        "tide_time": item["DateTime"],
                        "tide_level": pd.to_numeric(
                            item["TideHeights"]["Predicted"], errors="coerce"
                        ),
                        "tide_type": item["Tide"],
                        "lng": lng,
                        "lat": lat,
                        "data_time": data_time,
                    }
                )

    data = pd.DataFrame(rows)
    if data.empty:
        engine = create_engine(ready_data_db_uri)
        update_lasttime_in_data_to_dataset_info(engine, dag_id)
        raise ValueError("No tidal forecast data for target stations")

    gdata = add_point_wkbgeometry_column_to_df(
        data, data["lng"], data["lat"], from_crs=FROM_CRS
    )

    ready_data = gdata[
        [
            "data_time",
            "station_name",
            "station_id",
            "tide_time",
            "tide_level",
            "tide_type",
            "lng",
            "lat",
            "wkb_geometry",
        ]
    ]

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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0096")
dag.create_dag(etl_func=_R0096)
