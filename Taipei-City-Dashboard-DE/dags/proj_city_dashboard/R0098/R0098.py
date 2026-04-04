from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0098(**kwargs):
    import pandas as pd
    import requests
    from sqlalchemy import create_engine
    from utils.load_stage import (
        save_dataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )

    # Config
    dag_infos = kwargs.get("dag_infos")
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")

    URL = "https://data.ntpc.gov.tw/api/datasets/3cdc5b9c-ce48-4dd6-8079-b9b3fa4b7296/json"
    SIZE = 1000

    # Extract: paginate through all data with page (0-indexed) and size
    all_data = []
    page = 0
    while True:
        res = requests.get(URL, params={"page": page, "size": SIZE}, timeout=60)
        if res.status_code != 200:
            raise ValueError(f"data.ntpc API failed: {res.status_code}")
        records = res.json()
        if not records:
            break
        all_data.extend(records)
        page += 1

    if not all_data:
        raise ValueError("No data from New Taipei pump station API")

    raw_data = pd.DataFrame(all_data)

    # Transform: rename Chinese columns to English and add data_time
    col_map = {
        "抽水站名稱": "station_name",
        "地址": "address",
        "水系": "river_system",
        "竣工年度": "completion_year",
        "抽水機形式": "pump_type",
    }
    data = raw_data.rename(columns=col_map)
    data["data_time"] = pd.Timestamp.now(tz="Asia/Taipei")

    # Select output columns
    ready_data = data[[
        "data_time",
        "station_name",
        "address",
        "river_system",
        "completion_year",
        "pump_type",
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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0098")
dag.create_dag(etl_func=_R0098)
