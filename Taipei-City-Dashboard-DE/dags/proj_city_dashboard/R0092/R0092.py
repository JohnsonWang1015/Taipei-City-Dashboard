from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0092(**kwargs):
    import pandas as pd
    import requests
    from sqlalchemy import create_engine
    from utils.load_stage import (
        save_dataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )
    from utils.transform_time import convert_str_to_time_format

    # Config
    dag_infos = kwargs.get("dag_infos")
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")

    PAGE_ID = "6f03a0b8-7b98-4eea-8bb9-ba6bfcdc2b8b"
    URL = f"https://data.taipei/api/dataset/{PAGE_ID}?scope=resourceAquire"

    # Extract: paginate through all data
    all_data = []
    offset = 0
    limit = 1000
    while True:
        res = requests.get(
            URL, params={"offset": offset, "limit": limit}, timeout=60
        )
        if res.status_code != 200:
            raise ValueError(f"data.taipei API failed: {res.status_code}")
        result = res.json().get("result", {})
        records = result.get("results", [])
        if not records:
            break
        all_data.extend(records)
        offset += limit
        if offset >= result.get("count", 0):
            break

    if not all_data:
        raise ValueError("No data from Taipei rainfall API")

    raw_data = pd.DataFrame(all_data)

    # Transform
    data = raw_data.copy()
    col_map = {
        "stationNo": "station_no",
        "stationName": "station_name",
        "recTime": "rec_time_str",
        "rain": "rain_daily",
    }
    data = data.rename(columns=col_map)

    # Time conversion
    data["data_time"] = convert_str_to_time_format(
        data["rec_time_str"],
        from_format="%Y%m%d%H%M",
    )

    # Convert numeric
    data["rain_daily"] = pd.to_numeric(data["rain_daily"], errors="coerce")

    # Select output columns
    ready_data = data[[
        "data_time",
        "station_no",
        "station_name",
        "rain_daily",
    ]]

    # Load
    engine = create_engine(ready_data_db_uri)
    save_dataframe_to_postgresql(
        engine,
        data=ready_data,
        load_behavior=load_behavior,
        default_table=default_table,
        history_table=history_table,
    )
    lasttime_in_data = data["data_time"].max()
    update_lasttime_in_data_to_dataset_info(engine, dag_id, lasttime_in_data)


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0092")
dag.create_dag(etl_func=_R0092)
