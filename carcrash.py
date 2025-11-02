import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title="사고다발지역 안전지도",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 앱 기본 스타일: 흰 배경, 검은 글자
st.markdown(
    """
    <style>
    .css-18e3th9 {background-color: #ffffff;}
    .css-1d391kg {color: #000000;}
    .stButton>button {color: #000000; background-color: #f2f2f2;}
    .stSidebar {background-color: #ffffff;}
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------
# 유틸: 거리 계산 (Haversine)
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
# 데이터 로드
# -------------------------
@st.cache_data
def load_data(path="한국도로교통공단_교통사고다발지역_20250924.csv"):
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except Exception:
        df = pd.read_csv(path, encoding="cp949")
    df.columns = [c.strip() for c in df.columns]
    return df

data = load_data()

st.title("🛡️ 사고다발지역 안전지도 — 근사 안전경로 & 위험 레이어")
st.markdown(
    "이 앱은 한국도로교통공단의 사고다발지역 CSV를 사용해 **사고 위치 표출**, "
    "**히트맵/클러스터**, **필터/검색**, 그리고 **근사 안전경로(데이터 기반)**를 제공합니다."
)

# -------------------------
# 기본 컬럼 체크
# -------------------------
has_latlon = {"위도", "경도"}.issubset(set(data.columns))
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None
severity_related_cols = set(["사망자수","중상자수","경상자수","사고건수","사상자수"]) & set(data.columns)

# -------------------------
# 사이드바: 필터
# -------------------------
st.sidebar.header("🔎 필터 · 검색 · 안전경로")

# 연도 필터
if year_col:
    years = sorted(data[year_col].dropna().unique().astype(int))
    sel_year = st.sidebar.slider("📅 연도 선택", int(min(years)), int(max(years)), int(max(years)))
else:
    sel_year = None

# 사고유형 필터
if type_col:
    types = sorted(data[type_col].dropna().unique())
    sel_types = st.sidebar.multiselect("⚠️ 사고유형 필터", options=types, default=types)
else:
    sel_types = None

# 사고원인 필터
possible_cause_cols = [c for c in data.columns if "원인" in c or "사고원인" in c or "발생원인" in c]
cause_col = possible_cause_cols[0] if possible_cause_cols else None
if cause_col:
    causes = sorted(data[cause_col].dropna().unique())
    sel_causes = st.sidebar.multiselect("🧭 사고원인 필터", options=causes, default=causes)
else:
    sel_causes = None

# 검색(지역명/위치명)
search_text = st.sidebar.text_input("🔍 검색 (지역명 / 위치명)", "")

# -------------------------
# 데이터 필터링 적용
# -------------------------
df = data.copy()
if sel_year and year_col:
    df = df[df[year_col] == sel_year]
if sel_types and type_col:
    df = df[df[type_col].isin(sel_types)]
if sel_causes and cause_col:
    df = df[df[cause_col].isin(sel_causes)]
if search_text:
    text_cols = [c for c in df.columns if df[c].dtype == object]
    mask = pd.Series(False, index=df.index)
    for c in text_cols:
        mask |= df[c].astype(str).str.contains(search_text, case=False, na=False)
    df = df[mask]

# -------------------------
# 심각도 점수
# -------------------------
def severity_score(row):
    score = 0.0
    if "사망자수" in row.index:
        score += 10 * (row.get("사망자수",0) or 0)
    if "중상자수" in row.index:
        score += 3 * (row.get("중상자수",0) or 0)
    if "경상자수" in row.index:
        score += 1 * (row.get("경상자수",0) or 0)
    if "사고건수" in row.index:
        score += 0.5 * (row.get("사고건수",0) or 0)
    return score

df["sev_score"] = df.apply(severity_score, axis=1) if len(df)>0 else []

def severity_to_color(s):
    if s >= 10: return [180,0,0,200]
    elif s >= 5: return [230,40,40,180]
    elif s >= 2: return [255,140,0,150]
    elif s > 0: return [255,210,0,130]
    else: return [150,150,150,90]

df["color"] = df["sev_score"].apply(severity_to_color) if len(df)>0 else []

# -------------------------
# 지도 시각화 (뚜렷하게)
# -------------------------
if has_latlon:
    center_lat = float(df["위도"].mean())
    center_lon = float(df["경도"].mean())
    
    heat_layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["경도","위도"],
        aggregation="SUM",
        weight="sev_score",
        radiusPixels=60,
    )
    hex_layer = pdk.Layer(
        "HexagonLayer",
        data=df,
        get_position=["경도","위도"],
        radius=200,
        elevation_scale=50,
        elevation_range=[0,3000],
        pickable=True,
        extruded=True,
    )
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["경도","위도"],
        get_color="color",
        get_radius=60,
        pickable=True,
    )

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=6, pitch=0)
    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/streets-v12",  # 뚜렷한 지도
        initial_view_state=view_state,
        layers=[heat_layer, hex_layer, scatter_layer],
        tooltip={"html": "<b>{사고지역위치명}</b><br/>사고건수:{사고건수} / 사상자:{사상자수} / 심각도:{sev_score}"}
    )
    st.pydeck_chart(deck, use_container_width=True)
else:
    st.error("위도/경도 컬럼이 필요합니다.")

# -------------------------
# 통계 그래프
# -------------------------
st.subheader("📊 통계 요약")
if "사고다발지역시도시군구" in df.columns and "사고건수" in df.columns:
    by_dist = df.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수", title="구별 사고건수 Top 15")
    st.plotly_chart(fig, use_container_width=True)

if type_col and "사고건수" in df.columns:
    by_type = df.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig2 = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율")
    st.plotly_chart(fig2, use_container_width=True)

