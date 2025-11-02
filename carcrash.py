import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import gdown  # Google Drive 파일 다운로드

st.set_page_config(page_title="사고다발지역 안전지도(근사)", layout="wide")

# -------------------------
# 유틸: 거리(위도/경도) 계산 — Haversine (km)
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def haversine_vectorized(lat1, lon1, lat_arr, lon_arr):
    R = 6371.0
    lat1r = np.radians(lat1)
    lon1r = np.radians(lon1)
    lat2r = np.radians(lat_arr)
    lon2r = np.radians(lon_arr)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# -------------------------
# 데이터 로드 (Google Drive)
# -------------------------
@st.cache_data
def load_data_from_drive(drive_url):
    file_id = drive_url.split("/")[5]
    download_url = f"https://drive.google.com/uc?id={file_id}"
    local_path = "accidents.csv"
    gdown.download(download_url, local_path, quiet=True)

    encodings = ["utf-8", "cp949", "euc-kr"]
    for enc in encodings:
        try:
            df = pd.read_csv(local_path, encoding=enc, on_bad_lines="skip")
            df.columns = [c.strip() for c in df.columns]
            print(f"CSV 로드 성공: encoding={enc}")
            return df
        except Exception as e:
            print(f"CSV 로드 실패({enc}): {e}")
    raise ValueError("CSV를 읽을 수 없습니다. 인코딩 문제 확인 필요")

drive_link = "https://drive.google.com/file/d/1c3ULCZImSX4ns8F9cIE2wVsy8Avup8bu/view?usp=sharing"
data = load_data_from_drive(drive_link)

# -------------------------
# Streamlit UI
# -------------------------
st.title("🛡️ 사고다발지역 안전지도 — 근사 안전경로 & 위험 레이어")
st.markdown(
    "이 앱은 한국도로교통공단의 사고다발지역 CSV를 사용해 **사고 위치 표출**, **히트맵/클러스터**, "
    "**필터/검색**, 그리고 **근사 안전경로(데이터 기반)** 를 제공합니다.\n\n"
    ":warning: 실제 내비게이션(도로 네트워크 기반 경로)은 외부 라우팅 API가 필요합니다. "
    "여기서는 데이터만으로 가능한 근사(위험 회피) 방식을 사용합니다."
)

# -------------------------
# 기본 컬럼 체크 및 표준화
# -------------------------
has_latlon = {"위도", "경도"}.issubset(set(data.columns))
has_year = "사고연도" in data.columns or "연도" in data.columns
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None
severity_related_cols = set(["사망자수", "중상자수", "경상자수", "사고건수", "사상자수"]) & set(data.columns)

# -------------------------
# 사이드바: 필터 & 검색
# -------------------------
st.sidebar.header("🔎 필터 · 검색 · 안전경로")

if year_col:
    years = sorted(data[year_col].dropna().unique().astype(int))
    sel_year = st.sidebar.slider("연도 선택", min_value=int(min(years)), max_value=int(max(years)), value=int(max(years)))
else:
    sel_year = None

if type_col:
    types = sorted(data[type_col].dropna().unique())
    sel_types = st.sidebar.multiselect("사고유형 필터", options=types, default=types)
else:
    sel_types = None

possible_cause_cols = [c for c in data.columns if "원인" in c or "사고원인" in c or "발생원인" in c]
cause_col = possible_cause_cols[0] if possible_cause_cols else None
if cause_col:
    causes = sorted(data[cause_col].dropna().unique())
    sel_causes = st.sidebar.multiselect("사고원인 필터", options=causes, default=causes)
else:
    sel_causes = None

date_col = None
for c in data.columns:
    if "일자" in c or "date" in c.lower() or "날짜" in c:
        date_col = c
        break

if date_col:
    try:
        data[date_col + "_parsed"] = pd.to_datetime(data[date_col], errors="coerce")
        min_d = data[date_col + "_parsed"].min()
        max_d = data[date_col + "_parsed"].max()
        sel_dates = st.sidebar.date_input("기간 필터", value=(max_d.date(), max_d.date()), min_value=min_d.date(), max_value=max_d.date())
    except Exception:
        date_col = None

search_text = st.sidebar.text_input("검색(지역명 / 위치코드 / 위치명) — 빈칸=전체", "")

loc_name_col = None
for c in ["사고지역위치명", "사고다발지역시도시군구", "위치코드"]:
    if c in data.columns:
        loc_name_col = c
        break
loc_options = data[loc_name_col].astype(str).unique().tolist() if loc_name_col else []

st.sidebar.markdown("---")
st.sidebar.subheader("🚗 근사 안전경로(데이터 기반)")
start_sel = st.sidebar.selectbox("출발지 (데이터 위치 중 선택)", options=loc_options, index=0 if loc_options else -1)
end_sel = st.sidebar.selectbox("도착지 (데이터 위치 중 선택)", options=loc_options, index=len(loc_options)-1 if loc_options else -1)
candidate_count = st.sidebar.slider("경로 후보 수", 3, 9, 5)
samples_per_candidate = st.sidebar.slider("경로 샘플 점 개수(정밀도)", 10, 80, 30)
avoid_radius_km = st.sidebar.slider("위험 가중 반경 (km)", 0.2, 3.0, 0.7)

st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ 위험 구간 경고 (임의 위치)")
alert_lat = st.sidebar.number_input("위도 입력", value=float(data["위도"].mean()) if has_latlon else 37.56)
alert_lon = st.sidebar.number_input("경도 입력", value=float(data["경도"].mean()) if has_latlon else 126.97)
alert_radius_km = st.sidebar.slider("경고 반경 (km)", 0.1, 5.0, 0.5)

# -------------------------
# 데이터 필터링 적용
# -------------------------
df = data.copy()
if sel_year and year_col: df = df[df[year_col] == sel_year]
if sel_types and type_col: df = df[df[type_col].isin(sel_types)]
if sel_causes and cause_col: df = df[df[cause_col].isin(sel_causes)]
if date_col:
    start_d, end_d = sel_dates
    mask = (df[date_col + "_parsed"].dt.date >= start_d) & (df[date_col + "_parsed"].dt.date <= end_d)
    df = df[mask]
if search_text:
    search_text = search_text.strip()
    text_cols = [c for c in df.columns if df[c].dtype == object]
    mask = pd.Series(False, index=df.index)
    for c in text_cols:
        mask = mask | df[c].astype(str).str.contains(search_text, case=False, na=False)
    df = df[mask]

# -------------------------
# 심각도 계산
# -------------------------
def severity_score(row):
    score = 0.0
    if "사망자수" in row.index: score += 10.0 * (row.get("사망자수", 0) or 0)
    if "중상자수" in row.index: score += 3.0 * (row.get("중상자수", 0) or 0)
    if "경상자수" in row.index: score += 1.0 * (row.get("경상자수", 0) or 0)
    if "사고건수" in row.index: score += 0.5 * (row.get("사고건수", 0) or 0)
    return score

df["sev_score"] = df.apply(severity_score, axis=1) if len(df) > 0 else []

def severity_to_color(s):
    if s >= 10: return [180, 0, 0, 200]
    elif s >= 5: return [230, 40, 40, 180]
    elif s >= 2: return [255, 140, 0, 150]
    elif s > 0: return [255, 210, 0, 130]
    else: return [150, 150, 150, 90]

df["color"] = df["sev_score"].apply(severity_to_color) if len(df) > 0 else []

# -------------------------
# 지도 레이아웃
# -------------------------
st.subheader("지도 · 히트맵 · 클러스터 · 마커")
if not has_latlon:
    st.error("데이터에 '위도' / '경도' 컬럼이 필요합니다. 현재 파일에 해당 컬럼이 없습니다.")
else:
    center_lat = float(df["위도"].mean()) if not np.isnan(df["위도"].mean()) else 37.56
    center_lon = float(df["경도"].mean()) if not np.isnan(df["경도"].mean()) else 126.97

    layers = []

    heat_layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["경도", "위도"],
        aggregation="SUM",
        weight="sev_score" if "sev_score" in df.columns else None,
        radiusPixels=60,
    )
    layers.append(heat_layer)

    hex_layer = pdk.Layer(
        "HexagonLayer",
        data=df,
        get_position=["경도", "위도"],
        radius=200,
        elevation_scale=50,
        elevation_range=[0, 3000],
        pickable=True,
        extruded=True,
    )
    layers.append(hex_layer)

    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["경도", "위도"],
        get_color="color",
        get_radius=60,
        pickable=True,
    )
    layers.append(scatter)

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=6, pitch=0)
    tooltip = {
        "html": "<b>{사고지역위치명}</b><br/>사고건수: {사고건수} / 사상자: {사상자수} / 심각도:{sev_score}",
        "style": {"color": "white"}
    }
    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=layers,
        tooltip=tooltip
    )
    st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# 이하 통계, 위험 경고, 근사 경로, 마무리
# -------------------------
# ... 기존 코드 그대로 이어서 사용 ...
