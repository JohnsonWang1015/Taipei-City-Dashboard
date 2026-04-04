from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0101(**kwargs):
    import logging
    import re

    import geopandas as gpd
    import pandas as pd
    import requests
    from shapely import wkt
    from shapely.geometry import Point, Polygon, shape
    from sqlalchemy import create_engine
    from utils.get_time import get_tpe_now_time_str
    from utils.load_stage import (
        save_geodataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )
    from utils.transform_geometry import convert_geometry_to_wkbgeometry

    TAIPEI_KML_URL = "https://data.taipei/dataset/detail?id=08101966-7aca-48e0-a028-6da02ba1192e"
    NTPC_LOWLYING_URL = "https://data.ntpc.gov.tw/api/datasets/3674522f-e5a1-469f-9fd8-7f2c195427ad/json"

    def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
        lower_map = {str(col).lower(): col for col in df.columns}
        for cand in candidates:
            if cand.lower() in lower_map:
                return lower_map[cand.lower()]
        return None

    def _parse_district_from_description(val) -> str | None:
        if pd.isna(val):
            return None
        text = str(val)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return None

        pattern = r"(?:行政區|地區|區域|district)[：:\s]*([^;；,，\n\r]+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

        for token in re.split(r"[;；,，\n\r]", text):
            token = token.strip()
            if token.endswith("區"):
                return token
        return None

    def _to_polygon_geometry(row: dict):
        geo_obj = row.get("geometry")
        if isinstance(geo_obj, dict):
            try:
                geom = shape(geo_obj)
                if geom.geom_type in ["Polygon", "MultiPolygon"]:
                    return geom
            except Exception:
                pass
        elif isinstance(geo_obj, str) and geo_obj.strip():
            geo_str = geo_obj.strip()
            try:
                geom = wkt.loads(geo_str)
                if geom.geom_type in ["Polygon", "MultiPolygon"]:
                    return geom
            except Exception:
                pass

        for key in ["wkt", "geom", "the_geom", "geo", "shape"]:
            val = row.get(key)
            if not isinstance(val, str) or not val.strip():
                continue
            try:
                geom = wkt.loads(val.strip())
                if geom.geom_type in ["Polygon", "MultiPolygon"]:
                    return geom
            except Exception:
                continue

        for key in ["coordinates", "coord", "polygon", "rings"]:
            coords = row.get(key)
            if not isinstance(coords, list) or not coords:
                continue
            try:
                if isinstance(coords[0], list) and isinstance(coords[0][0], list):
                    ring = coords[0]
                else:
                    ring = coords
                polygon = Polygon(ring)
                if not polygon.is_empty:
                    return polygon
            except Exception:
                continue

        lon_keys = ["lon", "lng", "longitude", "x", "經度"]
        lat_keys = ["lat", "latitude", "y", "緯度"]
        lon = next((row.get(k) for k in lon_keys if row.get(k) not in [None, ""]), None)
        lat = next((row.get(k) for k in lat_keys if row.get(k) not in [None, ""]), None)
        if lon is not None and lat is not None:
            try:
                point = Point(float(lon), float(lat))
                return point.buffer(0.00001)
            except Exception:
                pass

        return None

    # Config
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_infos = kwargs.get("dag_infos")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Polygon"

    # Extract: Taipei KML
    taipei_data = gpd.GeoDataFrame(
        columns=["area_name", "district", "city", "geometry"],
        geometry="geometry",
        crs="EPSG:4326",
    )
    try:
        raw_taipei = gpd.read_file(TAIPEI_KML_URL, driver="KML")
        if not raw_taipei.empty:
            name_col = _find_col(raw_taipei, ["Name", "name"]) or "Name"
            desc_col = _find_col(raw_taipei, ["Description", "description"]) or "Description"

            taipei_data = raw_taipei.copy()
            taipei_data["area_name"] = taipei_data[name_col] if name_col in taipei_data.columns else None
            if desc_col in taipei_data.columns:
                taipei_data["district"] = taipei_data[desc_col].apply(_parse_district_from_description)
            else:
                taipei_data["district"] = None
            taipei_data["city"] = "台北市"
            taipei_data = taipei_data[["area_name", "district", "city", "geometry"]]
            if taipei_data.crs is None:
                taipei_data = taipei_data.set_crs(epsg=FROM_CRS)
    except Exception as e:
        logging.warning(f"R0101: Failed to parse Taipei KML, continue with NTPC only: {e}")

    # Extract: NTPC JSON
    ntpc_resp = requests.get(NTPC_LOWLYING_URL, timeout=60)
    if ntpc_resp.status_code != 200:
        raise ValueError(f"NTPC API request failed: {ntpc_resp.status_code}")

    ntpc_json = ntpc_resp.json()
    if isinstance(ntpc_json, list):
        ntpc_records = ntpc_json
    elif isinstance(ntpc_json, dict):
        ntpc_records = (
            ntpc_json.get("result", {}).get("records")
            or ntpc_json.get("records")
            or ntpc_json.get("data")
            or []
        )
    else:
        ntpc_records = []

    ntpc_rows = []
    for row in ntpc_records:
        if not isinstance(row, dict):
            continue

        area_name = (
            row.get("area_name")
            or row.get("name")
            or row.get("地區")
            or row.get("地點")
            or row.get("名稱")
        )
        district = (
            row.get("district")
            or row.get("行政區")
            or row.get("區")
            or row.get("鄉鎮市區")
        )
        geom = _to_polygon_geometry(row)

        ntpc_rows.append(
            {
                "area_name": area_name,
                "district": district,
                "city": "新北市",
                "geometry": geom,
            }
        )

    ntpc_data = gpd.GeoDataFrame(ntpc_rows, geometry="geometry", crs=f"EPSG:{FROM_CRS}")

    # Transform: merge two sources and standardize
    merged = pd.concat([taipei_data, ntpc_data], ignore_index=True)
    merged["data_time"] = get_tpe_now_time_str(is_with_tz=True)
    gdata = gpd.GeoDataFrame(merged, geometry="geometry", crs=f"EPSG:{FROM_CRS}")

    try:
        gdata = convert_geometry_to_wkbgeometry(gdata, from_crs=FROM_CRS)
    except Exception as e:
        logging.error(f"R0101: Geometry conversion failed: {e}")
        raise
        gdata["wkb_geometry"] = None

    ready_data = gdata[["area_name", "district", "city", "data_time", "wkb_geometry"]]

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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0101")
dag.create_dag(etl_func=_R0101)
