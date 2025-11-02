import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title="🛡️ 사고다발지역 안전지도",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 스타일: 흰색 배경, 검은 글씨
st.markdown("""
<style>
body { background-color: white; color: black; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Haversine 거리 계산
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# -------------------------
# 데이터 로드
# -------------------------
@st.cache_data
def load_data(url="https://drive.google.com/uc?id=1c3ULCZImSX4ns8F9cIE2wVsy8Avup8bu&export=download"):
    try:
        df = pd.read_csv(url, encoding="utf-8")
    except:
        df = pd.read_csv(url, encoding="cp949")
    df.columns = [c.strip() for c in df.columns]
    return df

data = load_data()

# -------------------------
# 체크
# -------------------------
has_latlon = {"위도","경도"}.issubset(set(data.columns))
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None

# -------------------------
# 사이드바 필터
# -------------------------
st.sidebar.header("🔎 필터 · 검색 ")

if year_col:
    years = sorted(data[year_col].dropna().unique().astype(int))
    sel_year_range = st.sidebar.slider(
        "연도 범위 선택",
        min_value=int(min(years)),
        max_value=int(max(years)),
        value=(int(min(years)), int(max(years)))
    )
else:
    sel_year_range = None

if type_col:
    types = sorted(data[type_col].dropna().unique())
    sel_types = st.sidebar.multiselect("사고유형 필터", options=types, default=types)
else:
    sel_types = None

# -------------------------
# 데이터 필터링
# -------------------------
df = data.copy()
if sel_year_range and year_col:
    df = df[(df[year_col] >= sel_year_range[0]) & (df[year_col] <= sel_year_range[1])]
if sel_types and type_col:
    df = df[df[type_col].isin(sel_types)]

# -------------------------
# 심각도 계산
# -------------------------
def severity_score(row):
    score = 0.0
    if "사망자수" in row.index: score += 10.0 * (row.get("사망자수",0) or 0)
    if "중상자수" in row.index: score += 3.0 * (row.get("중상자수",0) or 0)
    if "경상자수" in row.index: score += 1.0 * (row.get("경상자수",0) or 0)
    if "사고건수" in row.index: score += 0.5 * (row.get("사고건수",0) or 0)
    return score

df["sev_score"] = df.apply(severity_score, axis=1)

def severity_to_color(s):
    if s >= 10: return [180,0,0,200]
    elif s >=5: return [230,40,40,180]
    elif s >=2: return [255,140,0,150]
    elif s >0: return [255,210,0,130]
    else: return [150,150,150,90]

df["color"] = df["sev_score"].apply(severity_to_color)

# -------------------------
# 타이틀
# -------------------------
st.title("🛡️ 사고다발지역 안전지도")
st.markdown("사고 데이터 기반 시각화")

# -------------------------
# 지도 시각화
# -------------------------
if not has_latlon:
    st.error("위도/경도 컬럼 필요")
else:
    center_lat = float(df["위도"].mean())
    center_lon = float(df["경도"].mean())

    # 레이어 설정
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["경도","위도"],
        get_color="color",
        get_radius=60,
        pickable=True,
        auto_highlight=True
    )

    heat_layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["경도","위도"],
        aggregation="SUM",
        weight="sev_score",
        radiusPixels=60
    )

    layers = [heat_layer, scatter_layer]

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=7,
        pitch=0
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v9",
        controller=False  # 이동/확대/축소 막기
    )

    st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# 통계
# -------------------------
st.subheader("📊 통계")
if "사고다발지역시도시군구" in df.columns and "사고건수" in df.columns:
    by_dist = df.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구"], y="사고건수", title="구별 사고건수 Top 15")
    st.plotly_chart(fig, use_container_width=True)

if type_col and "사고건수" in df.columns:
    by_type = df.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig2 = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율")
    st.plotly_chart(fig2, use_container_width=True)
