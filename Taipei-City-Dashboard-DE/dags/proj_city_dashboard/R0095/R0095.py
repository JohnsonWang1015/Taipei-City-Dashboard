from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0095(**kwargs):
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

    URL = (
        "https://data.taipei/api/dataset/"
        "cc3f7e86-77ec-4bd3-a09f-05b175e192f5?scope=resourceAquire"
    )

    # Extract: paginate through all data
    all_data = []
    offset = 0
    limit = 1000
    while True:
        res = requests.get(
            URL,
            params={"offset": offset, "limit": limit},
            timeout=60,
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
        raise ValueError("No data from Taipei floodgate status API")

    raw_data = pd.DataFrame(all_data)

    # Transform
    data = raw_data.copy()

    def _count_flag_columns(row, prefix):
        count = 0
        for idx in range(1, 21):
            col = f"{prefix}{idx:02d}"
            if str(row.get(col, "")).strip() == "1":
                count += 1
        return count

    data["gate_open"] = data.apply(
        lambda row: _count_flag_columns(row, "fo"), axis=1
    )
    data["gate_close"] = data.apply(
        lambda row: _count_flag_columns(row, "fc"), axis=1
    )
    data["gate_total"] = pd.to_numeric(
        data.get("GateNum"), errors="coerce"
    ).astype("Int64")

    data["data_time"] = convert_str_to_time_format(
        data["recTime"],
        from_format="%Y%m%d%H%M",
    )

    data = data.rename(
        columns={
            "stationNo": "station_no",
            "stationName": "station_name",
        }
    )

    # Select output columns
    ready_data = data[
        [
            "data_time",
            "station_no",
            "station_name",
            "gate_total",
            "gate_open",
            "gate_close",
        ]
    ]

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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0095")
dag.create_dag(etl_func=_R0095)
