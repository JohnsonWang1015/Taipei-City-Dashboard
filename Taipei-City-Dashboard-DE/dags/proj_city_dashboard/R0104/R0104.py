from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0104(**kwargs):
    import logging

    import pandas as pd
    import requests
    from sqlalchemy import create_engine
    from utils.load_stage import (
        save_geodataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )
    from utils.transform_geometry import add_point_wkbgeometry_column_to_df

    TAIPEI_CCTV_URL_API = (
        "https://data.taipei/api/dataset/9dca148b-7ee3-422e-a53e-db70ab5b236a"
        "?scope=resourceAquire"
    )
    TAIPEI_CCTV_LOCATION_URL = "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=d317a3c4-ff08-48af-894e-31dfb5155de3"
    WRA_CCTV_URL = "https://fhy.wra.gov.tw/Api"
    PAGE_SIZE = 1000
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    def _extract_records(payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, dict):
                records = result.get("results")
                if isinstance(records, list):
                    return records
            records = payload.get("results")
            if isinstance(records, list):
                return records
            records = payload.get("data")
            if isinstance(records, list):
                return records
        return []

    def _get_first_existing_col(df, candidates):
        for col in candidates:
            if col in df.columns:
                return col
        return None

    # Config
    dag_infos = kwargs.get("dag_infos")
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")

    # Extract: Taipei CCTV stream URLs (paginated by offset/limit)
    taipei_url_rows = []
    offset = 0
    while True:
        res = requests.get(
            TAIPEI_CCTV_URL_API,
            params={"offset": offset, "limit": PAGE_SIZE},
            timeout=60,
        )
        res.raise_for_status()
        page_rows = _extract_records(res.json())
        if not page_rows:
            break
        taipei_url_rows.extend(page_rows)
        if len(page_rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    taipei_url_df = pd.DataFrame(taipei_url_rows)
    if taipei_url_df.empty:
        raise ValueError("No Taipei CCTV URL data returned")

    station_no_col = _get_first_existing_col(taipei_url_df, ["stationNo", "station_no"])
    station_name_col = _get_first_existing_col(taipei_url_df, ["stationName", "station_name"])
    stream_url_col = _get_first_existing_col(taipei_url_df, ["url", "stream_url"])
    if not station_no_col or not station_name_col or not stream_url_col:
        raise ValueError("Taipei CCTV URL payload missing required fields")

    taipei_url_df = taipei_url_df.rename(
        columns={
            station_no_col: "station_no",
            station_name_col: "station_name",
            stream_url_col: "stream_url",
        }
    )[["station_no", "station_name", "stream_url"]]

    # Extract: Taipei CCTV location coordinates
    loc_res = requests.get(TAIPEI_CCTV_LOCATION_URL, timeout=60)
    loc_res.raise_for_status()
    taipei_loc_df = pd.DataFrame(_extract_records(loc_res.json()))
    if not taipei_loc_df.empty:
            loc_station_no_col = _get_first_existing_col(taipei_loc_df, ["stationNo", "station_no"])
            loc_lng_col = _get_first_existing_col(taipei_loc_df, ["lng", "lon", "longitude", "x", "經度"])
            loc_lat_col = _get_first_existing_col(taipei_loc_df, ["lat", "latitude", "y", "緯度"])
            if loc_station_no_col and loc_lng_col and loc_lat_col:
                taipei_loc_df = taipei_loc_df.rename(columns={
                    loc_station_no_col: "station_no", loc_lng_col: "lng", loc_lat_col: "lat",
                })[["station_no", "lng", "lat"]]
                taipei_loc_df["lng"] = pd.to_numeric(taipei_loc_df["lng"], errors="coerce")
                taipei_loc_df["lat"] = pd.to_numeric(taipei_loc_df["lat"], errors="coerce")
            else:
                taipei_loc_df = pd.DataFrame(columns=["station_no", "lng", "lat"])

    # Transform: merge Taipei CCTV URLs + locations
    taipei_df = taipei_url_df.merge(taipei_loc_df, on="station_no", how="left")
    taipei_df["source"] = "台北市"

    # Extract: WRA CCTV
    wra_res = requests.get(WRA_CCTV_URL, timeout=60)
    wra_res.raise_for_status()
    wra_df = pd.DataFrame(_extract_records(wra_res.json()))

    if not wra_df.empty:
        wra_station_name_col = _get_first_existing_col(wra_df, ["station_name", "stationName", "name", "測站名稱"])
        wra_stream_url_col = _get_first_existing_col(wra_df, ["stream_url", "url", "video_url", "影像URL", "影像網址"])
        wra_lng_col = _get_first_existing_col(wra_df, ["lng", "lon", "longitude", "x", "經度"])
        wra_lat_col = _get_first_existing_col(wra_df, ["lat", "latitude", "y", "緯度"])
        if wra_station_name_col and wra_stream_url_col and wra_lng_col and wra_lat_col:
            wra_df = wra_df.rename(columns={
                wra_station_name_col: "station_name", wra_stream_url_col: "stream_url",
                wra_lng_col: "lng", wra_lat_col: "lat",
            })[["station_name", "stream_url", "lng", "lat"]]
            wra_df["lng"] = pd.to_numeric(wra_df["lng"], errors="coerce")
            wra_df["lat"] = pd.to_numeric(wra_df["lat"], errors="coerce")
            wra_df["source"] = "水利署"
        else:
            wra_df = pd.DataFrame()

    # Combine sources and add current timestamp
    frames = [taipei_df[["station_name", "stream_url", "source", "lng", "lat"]]]
    if not wra_df.empty:
        frames.append(wra_df[["station_name", "stream_url", "source", "lng", "lat"]])
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.dropna(subset=["lng", "lat"]).copy()
    if merged.empty:
        raise ValueError("No valid CCTV rows with coordinates after merge")

    merged["data_time"] = pd.Timestamp.now(tz="Asia/Taipei")

    # Geometry
    gdata = add_point_wkbgeometry_column_to_df(
        merged, merged["lng"], merged["lat"], from_crs=FROM_CRS
    )

    # Output columns
    ready_data = gdata[
        [
            "station_name",
            "stream_url",
            "source",
            "lng",
            "lat",
            "data_time",
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
    update_lasttime_in_data_to_dataset_info(engine, dag_id, ready_data["data_time"].max())


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0104")
dag.create_dag(etl_func=_R0104)
