from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0099(**kwargs):
    import pandas as pd
    import requests
    from sqlalchemy import create_engine
    from utils.get_time import get_tpe_now_time_str
    from utils.load_stage import (
        save_dataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )

    # Config
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_infos = kwargs.get("dag_infos")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")

    DATASET_ID = "bf784279-31aa-44bc-a210-33151d03e7ab"
    PAGE_SIZE = 1000

    # Extract with pagination
    all_rows = []
    page = 0
    while True:
        resp = requests.get(
            f"https://data.ntpc.gov.tw/api/datasets/{DATASET_ID}/json",
            params={"page": page, "size": PAGE_SIZE},
            timeout=60,
        )
        if resp.status_code != 200:
            raise ValueError(f"Request failed: {resp.status_code}")

        page_data = resp.json()
        if not isinstance(page_data, list) or not page_data:
            break

        all_rows.extend(page_data)
        if len(page_data) < PAGE_SIZE:
            break
        page += 1

    raw_data = pd.DataFrame(all_rows)
    if raw_data.empty:
        raise ValueError("No floodgate data returned from data.ntpc API")

    # Transform
    data = raw_data.copy()
    rename_map = {
        "水門名稱": "gate_name",
        "抽水站名稱": "station_name",
        "水系": "river_system",
        "行政區": "district",
    }
    data = data.rename(columns=rename_map)

    for col in ["gate_name", "station_name", "river_system", "district"]:
        if col not in data.columns:
            data[col] = None

    data["data_time"] = get_tpe_now_time_str(is_with_tz=True)

    # Select output columns
    ready_data = data[["gate_name", "station_name", "river_system", "district", "data_time"]]

    # Load
    engine = create_engine(ready_data_db_uri)
    save_dataframe_to_postgresql(
        engine,
        data=ready_data,
        load_behavior=load_behavior,
        default_table=default_table,
        history_table=history_table,
    )
    update_lasttime_in_data_to_dataset_info(
        engine, dag_id, ready_data["data_time"].max()
    )


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0099")
dag.create_dag(etl_func=_R0099)
