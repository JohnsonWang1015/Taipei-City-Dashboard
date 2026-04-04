from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0097(**kwargs):
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

    # Extract
    primary_url = "https://246.swcb.gov.tw/Service/OpenData/AlertInfo"
    fallback_url = "https://data.ardswc.gov.tw/Data/OpenData/Api"

    raw_data = []
    for url in [primary_url, fallback_url]:
        try:
            res = requests.get(url, timeout=60)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, list):
                raw_data = data
                break
        except Exception:
            continue

    if not raw_data:
        import logging

        logging.warning("R0097: No debris flow warning data returned (may be normal outside alert periods)")
        engine = create_engine(ready_data_db_uri)
        update_lasttime_in_data_to_dataset_info(engine, dag_id)
        return

    # Transform
    filtered_data = [
        row
        for row in raw_data
        if any(keyword in row.get("County", "") for keyword in ["新北", "台北"])
    ]

    if not filtered_data:
        data = pd.DataFrame(
            columns=[
                "stream_id",
                "stream_name",
                "alert_level",
                "village",
                "township",
                "county",
                "data_time",
            ]
        )
    else:
        data = pd.DataFrame(filtered_data)
        data = data.rename(
            columns={
                "DebrisFlowStreamID": "stream_id",
                "DebrisFlowStreamName": "stream_name",
                "AlertLevel": "alert_level",
                "Village": "village",
                "Township": "township",
                "County": "county",
            }
        )

        if "stream_id" not in data.columns:
            data["stream_id"] = None
        if "stream_name" not in data.columns:
            data["stream_name"] = None
        if "alert_level" not in data.columns:
            data["alert_level"] = None
        if "village" not in data.columns:
            data["village"] = None
        if "township" not in data.columns:
            data["township"] = None
        if "county" not in data.columns:
            data["county"] = None

        data["data_time"] = pd.Timestamp.now(tz="Asia/Taipei")

    ready_data = data[
        [
            "stream_id",
            "stream_name",
            "alert_level",
            "village",
            "township",
            "county",
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
    update_lasttime_in_data_to_dataset_info(
        engine, dag_id, ready_data["data_time"].max()
    )


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0097")
dag.create_dag(etl_func=_R0097)
