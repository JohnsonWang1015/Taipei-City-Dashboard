from airflow import DAG
from operators.common_pipeline import CommonDag


def _R0100(**kwargs):
    import html
    import re
    import xml.etree.ElementTree as ET

    import pandas as pd
    import requests
    from sqlalchemy import create_engine
    from utils.load_stage import (
        save_geodataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )
    from utils.transform_geometry import (
        add_point_wkbgeometry_column_to_df,
        convert_geometry_to_wkbgeometry,
    )

    def _strip_html(text):
        if text is None:
            return ""
        text = str(text)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"[\t\r]+", " ", text)
        text = re.sub(r" +", " ", text)
        return text.strip()

    def _extract_first_match(patterns, text):
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _parse_description_fields(description):
        clean_text = _strip_html(description)
        date = _extract_first_match(
            [r"(?:日期|發生日期|事件日期|時間)[:：\s]*([0-9]{4}[/-][0-9]{1,2}[/-][0-9]{1,2})",
             r"(?:日期|發生日期|事件日期|時間)[:：\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)"],
            clean_text,
        )
        depth_raw = _extract_first_match(
            [r"(?:積水深度|水深|深度)[:：\s]*([0-9]+(?:\.[0-9]+)?\s*(?:cm|公分|公尺|m|mm|毫米)?)"],
            clean_text,
        )
        district = _extract_first_match(
            [r"(?:行政區|地區|區域|轄區)[:：\s]*([^\s,，;；]+區)", r"([^\s,，;；]+區)"],
            clean_text,
        )
        depth = None
        if depth_raw:
            value_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", depth_raw)
            if value_match:
                depth = float(value_match.group(1))
                unit = depth_raw.lower()
                if "mm" in unit or "毫米" in unit:
                    depth = depth / 10
                elif "m" in unit or "公尺" in unit:
                    depth = depth * 100
        return {"date": date, "depth": depth, "district": district}

    def _parse_coordinates(coord_text):
        parts = [part.strip() for part in str(coord_text).split(",")]
        if len(parts) < 2:
            return None, None
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None, None

    def _parse_kml_with_xml(kml_text):
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        root = ET.fromstring(kml_text)
        rows = []
        for placemark in root.findall(".//kml:Placemark", ns):
            name = placemark.findtext("kml:name", default="", namespaces=ns)
            description = placemark.findtext("kml:description", default="", namespaces=ns)
            coord_text = placemark.findtext(".//kml:Point/kml:coordinates", default="", namespaces=ns)
            if not coord_text:
                coord_text = placemark.findtext(".//kml:coordinates", default="", namespaces=ns)
            lng, lat = _parse_coordinates(coord_text)
            rows.append({"name": name, "description": description, "lng": lng, "lat": lat})
        return pd.DataFrame(rows)

    def _normalize_date_column(date_series):
        normalized = (
            date_series.astype(str)
            .str.replace("年", "-", regex=False)
            .str.replace("月", "-", regex=False)
            .str.replace("日", "", regex=False)
            .str.replace("/", "-", regex=False)
            .str.strip()
        )
        return pd.to_datetime(normalized, errors="coerce").dt.date

    # Config
    dag_infos = kwargs.get("dag_infos")
    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    proxies = kwargs.get("proxies")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")

    KML_URL = "https://data.taipei/dataset/detail?id=8377b584-81e9-432d-b902-5b4e9978e6bc"
    FROM_CRS = 4326
    GEOMETRY_TYPE = "Point"

    # Extract
    raw_data = None
    geo_loaded = False
    geo_raw = None
    try:
        import geopandas as gpd

        geo_raw = gpd.read_file(KML_URL, driver="KML")
        geo_loaded = True
        raw_data = pd.DataFrame(geo_raw.drop(columns="geometry", errors="ignore")).copy()
        raw_data.columns = raw_data.columns.str.lower()
        if "name" not in raw_data.columns:
            raw_data["name"] = None
        if "description" not in raw_data.columns:
            raw_data["description"] = None
    except Exception:
        res = requests.get(KML_URL, timeout=120, proxies=proxies)
        res.raise_for_status()
        raw_data = _parse_kml_with_xml(res.text)

    if raw_data is None or raw_data.empty:
        raise ValueError("No KML placemark data was extracted.")

    # Transform
    data = raw_data.copy()
    data["location"] = data.get("name")
    parsed_fields = data.get("description", pd.Series(index=data.index)).apply(
        _parse_description_fields
    )
    parsed_df = pd.DataFrame(parsed_fields.tolist(), index=data.index)
    data = pd.concat([data, parsed_df], axis=1)

    data["district"] = data["district"].fillna(
        data["location"].astype(str).str.extract(r"([^\s,，;；]+區)", expand=False)
    )

    data["date"] = _normalize_date_column(data["date"])
    data["month"] = pd.to_datetime(data["date"], errors="coerce").dt.month.astype("Int64")
    data["data_time"] = pd.Timestamp.now().floor("s")

    # Geometry
    if geo_loaded and geo_raw is not None:
        gdata = geo_raw.copy()
        gdata.columns = gdata.columns.str.lower()

        if gdata.crs is None:
            gdata = gdata.set_crs(epsg=FROM_CRS)
        else:
            gdata = gdata.to_crs(epsg=FROM_CRS)

        gdata["geometry"] = gdata["geometry"].apply(
            lambda geom: geom if (geom is None or geom.geom_type == "Point") else geom.representative_point()
        )
        gdata["lng"] = gdata.geometry.x
        gdata["lat"] = gdata.geometry.y

        gdata["location"] = data["location"]
        gdata["district"] = data["district"]
        gdata["date"] = data["date"]
        gdata["depth"] = pd.to_numeric(data["depth"], errors="coerce")
        gdata["month"] = data["month"]
        gdata["data_time"] = data["data_time"]

        gdata = convert_geometry_to_wkbgeometry(gdata, from_crs=FROM_CRS)
        ready_data = gdata[
            [
                "data_time",
                "location",
                "district",
                "date",
                "depth",
                "month",
                "lng",
                "lat",
                "wkb_geometry",
            ]
        ].copy()
    else:
        data["lng"] = pd.to_numeric(data.get("lng"), errors="coerce")
        data["lat"] = pd.to_numeric(data.get("lat"), errors="coerce")
        data = data.dropna(subset=["lng", "lat"]).copy()
        data["depth"] = pd.to_numeric(data["depth"], errors="coerce")

        data = add_point_wkbgeometry_column_to_df(
            data,
            data["lng"],
            data["lat"],
            from_crs=FROM_CRS,
        )

        ready_data = data[
            [
                "data_time",
                "location",
                "district",
                "date",
                "depth",
                "month",
                "lng",
                "lat",
                "wkb_geometry",
            ]
        ].copy()

    if ready_data.empty:
        raise ValueError("No valid rows after geometry parsing.")

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


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="R0100")
dag.create_dag(etl_func=_R0100)
