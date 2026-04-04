from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0103(**kwargs):
    import pandas as pd
    import requests
    from sqlalchemy import create_engine
    from utils.load_stage import (
        save_geodataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )
    from utils.transform_geometry import add_point_wkbgeometry_column_to_df

    # Config
    dag_infos = kwargs.get("dag_infos")
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")

    TPE_URL = "https://data.taipei/api/dataset/aaf97773-3631-40e2-b3cc-da87bf2ce1d5?scope=resourceAquire"
    NTPC_URL = "https://data.ntpc.gov.tw/api/datasets/25E439AB-49E7-4E5E-85CE-A25C13FD2770/json?page=0&size=1000"
    NATIONAL_SHELTER_URL = "https://opdadm.moi.gov.tw/api/v1/no-auth/resource/api/dataset/ED6CF735-6C03-4573-A882-72C1BEC799CB/resource/54550E2F-4567-4C8F-BD2E-E54E9D0386B8/download"

    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    def _get_first_value(row, keys):
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            return value
        return None

    def _to_int(value):
        num = pd.to_numeric(value, errors="coerce")
        if pd.isna(num):
            return pd.NA
        return int(num)

    def _extract_tpe_records():
        records = []
        offset = 0
        limit = 1000
        while True:
            res = requests.get(
                TPE_URL,
                params={"offset": offset, "limit": limit},
                timeout=60,
            )
            if res.status_code != 200:
                raise ValueError(f"data.taipei API failed: {res.status_code}")

            payload = res.json().get("result", {})
            page_records = payload.get("results", [])
            if not page_records:
                break

            records.extend(page_records)
            offset += limit
            if offset >= payload.get("count", 0):
                break

        return records

    def _extract_ntpc_records():
        records = []
        page = 0
        size = 1000
        base_url = NTPC_URL.split("?")[0]
        while True:
            res = requests.get(
                base_url,
                params={"page": page, "size": size},
                timeout=60,
            )
            if res.status_code != 200:
                raise ValueError(f"data.ntpc API failed: {res.status_code}")

            page_records = res.json()
            if not page_records:
                break

            records.extend(page_records)
            page += 1

        return records

    def _extract_national_records():
        res = requests.get(NATIONAL_SHELTER_URL, timeout=60)
        if res.status_code != 200:
            raise ValueError(
                f"National shelter source API failed: {res.status_code}"
            )

        payload = res.json()
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("result", {}).get("results"), list):
                return payload["result"]["results"]
            if isinstance(payload.get("results"), list):
                return payload["results"]
            if isinstance(payload.get("data"), list):
                return payload["data"]

        return []

    def _standardize_records(records, source_name):
        if not records:
            return pd.DataFrame(
                columns=[
                    "shelter_name",
                    "address",
                    "capacity",
                    "district",
                    "city",
                    "lng",
                    "lat",
                    "data_time",
                ]
            )

        standardized = []
        now_ts = pd.Timestamp.now(tz="Asia/Taipei")

        for row in records:
            shelter_name = _get_first_value(
                row,
                [
                    "場所名稱",
                    "收容處所名稱",
                    "避難收容處所名稱",
                    "shelter_name",
                    "name",
                    "Name",
                ],
            )
            address = _get_first_value(
                row,
                [
                    "地址",
                    "場所地址",
                    "收容處所地址",
                    "address",
                    "Address",
                ],
            )
            capacity = _to_int(
                _get_first_value(
                    row,
                    [
                        "容納人數",
                        "可收容人數",
                        "capacity",
                        "Capacity",
                    ],
                )
            )
            district = _get_first_value(
                row,
                [
                    "行政區",
                    "區",
                    "district",
                    "District",
                ],
            )
            lng = pd.to_numeric(
                _get_first_value(
                    row,
                    [
                        "經度",
                        "longitude",
                        "Longitude",
                        "lon",
                        "lng",
                        "x",
                    ],
                ),
                errors="coerce",
            )
            lat = pd.to_numeric(
                _get_first_value(
                    row,
                    [
                        "緯度",
                        "latitude",
                        "Latitude",
                        "lat",
                        "y",
                    ],
                ),
                errors="coerce",
            )

            if source_name == "taipei":
                city = "台北市"
            elif source_name == "new_taipei":
                city = "新北市"
            else:
                city_value = _get_first_value(
                    row,
                    [
                        "縣市",
                        "縣市別",
                        "city",
                        "City",
                    ],
                )
                if city_value in ["台北市", "臺北市"]:
                    city = "台北市"
                elif city_value in ["新北市"]:
                    city = "新北市"
                else:
                    city = "其他"

            standardized.append(
                {
                    "shelter_name": shelter_name,
                    "address": address,
                    "capacity": capacity,
                    "district": district,
                    "city": city,
                    "lng": lng,
                    "lat": lat,
                    "data_time": now_ts,
                }
            )

        data = pd.DataFrame(standardized)
        data["capacity"] = pd.to_numeric(data["capacity"], errors="coerce").astype("Int64")
        return data

    # Extract
    tpe_records = _extract_tpe_records()
    ntpc_records = _extract_ntpc_records()
    national_records = _extract_national_records()

    # Transform
    tpe_data = _standardize_records(tpe_records, source_name="taipei")
    ntpc_data = _standardize_records(ntpc_records, source_name="new_taipei")
    national_data = _standardize_records(national_records, source_name="national")

    data = pd.concat([tpe_data, ntpc_data, national_data], ignore_index=True)
    if data.empty:
        return

    data = data[data["city"].isin(["台北市", "新北市"])].copy()
    data = data.dropna(subset=["lng", "lat"]).reset_index(drop=True)
    if data.empty:
        return

    data = add_point_wkbgeometry_column_to_df(
        data,
        data["lng"],
        data["lat"],
        from_crs=FROM_CRS,
    )

    ready_data = data[
        [
            "data_time",
            "shelter_name",
            "address",
            "capacity",
            "district",
            "city",
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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0103")
dag.create_dag(etl_func=_R0103)
