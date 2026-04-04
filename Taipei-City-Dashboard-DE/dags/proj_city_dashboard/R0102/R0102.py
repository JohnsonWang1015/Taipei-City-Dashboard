from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0102(**kwargs):
    from datetime import datetime

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

    BASE_URL = "https://fhy.wra.gov.tw/WraApi/v1/Event/Year"
    start_year = 2015
    end_year = datetime.now().year

    # Extract: iterate by year and skip empty responses
    yearly_frames = []
    for year in range(start_year, end_year + 1):
        url = f"{BASE_URL}/{year}"
        res = requests.get(url, timeout=60)
        if res.status_code != 200:
            raise ValueError(f"WRA Event API failed for year {year}: {res.status_code}")

        year_json = res.json()
        if not year_json:
            continue

        year_df = pd.DataFrame(year_json)
        if year_df.empty:
            continue

        yearly_frames.append(year_df)

    if not yearly_frames:
        print("!!!data is empty!!!")
        return "!!!data is empty!!!"

    raw_data = pd.concat(yearly_frames, ignore_index=True)

    # Transform
    data = raw_data.copy()
    col_map = {
        "EventNo": "event_no",
        "EventName": "event_name",
        "EventYear": "event_year",
        "StartDate": "start_date",
        "EndDate": "end_date",
        "EventType": "event_type",
    }
    data = data.rename(columns=col_map)

    # Ensure all target columns exist
    required_columns = [
        "event_no",
        "event_name",
        "event_year",
        "start_date",
        "end_date",
        "event_type",
    ]
    for col in required_columns:
        if col not in data.columns:
            data[col] = None

    data["start_date"] = pd.to_datetime(data["start_date"], errors="coerce")
    data["end_date"] = pd.to_datetime(data["end_date"], errors="coerce")
    data["event_year"] = pd.to_numeric(data["event_year"], errors="coerce")
    data["data_time"] = pd.Timestamp.now()

    ready_data = data[
        [
            "event_no",
            "event_name",
            "event_year",
            "start_date",
            "end_date",
            "event_type",
            "data_time",
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
    lasttime_in_data = ready_data["data_time"].max()
    update_lasttime_in_data_to_dataset_info(engine, dag_id, lasttime_in_data)


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0102")
dag.create_dag(etl_func=_R0102)
