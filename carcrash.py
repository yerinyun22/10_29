import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
import json
import requests
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title="🛡️ 사고다발지역 안전지도",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# 💡 흰 배경 + 검은 글씨 + selectbox 흰색
# -------------------------
st.markdown("""
<style>
body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
    background-color: white !important;
    color: black !important;
}
[data-testid="stSidebar"] {
    background-color: #f9f9f9 !important;
}
h1, h2, h3, h4, h5, h6, p, label, div {
    color: black !important;
}
/* 📊 보고 싶은 통계 유형 선택 바 스타일 */
div[data-testid="stSelectbox"] {
    background-color: white !important;
    border-radius: 8px !important;
    padding: 4px;
}
div[data-testid="stSelectbox"] label {
    color: black !important;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# 유틸: 거리 계산
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
# 대한민국 행정구역 GeoJSON 불러오기 (윤곽선용)
# -------------------------
@st.cache_data
def load_korea_boundary():
    url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea-provinces-geo.json"
    try:
        res = requests.get(url)
        geojson = res.json()
        return geojson
    except:
        return None

korea_geo = load_korea_boundary()

# -------------------------
# 컬럼 확인
# -------------------------
has_latlon = {"위도", "경도"}.issubset(set(data.columns))
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None

# -------------------------
# 사이드바
# -------------------------
st.sidebar.header("🔎 옵션 설정")

mode = st.sidebar.radio("화면 모드 선택", ["지도 보기", "통계 보기"])

if year_col:
    years = sorted(data[year_col].dropna().unique().astype(int))
    sel_year_range = st.sidebar.slider("연도 범위 선택", min_value=int(min(years)), max_value=int(max(years)),
                                       value=(int(min(years)), int(max(years))))
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
# 심각도 계산 및 색상 강화
# -------------------------
def severity_score(row):
    score = 0.0
    if "사망자수" in row.index: score += 10 * (row.get("사망자수", 0) or 0)
    if "중상자수" in row.index: score += 3 * (row.get("중상자수", 0) or 0)
    if "경상자수" in row.index: score += 1 * (row.get("경상자수", 0) or 0)
    if "사고건수" in row.index: score += 0.5 * (row.get("사고건수", 0) or 0)
    return score

df["sev_score"] = df.apply(severity_score, axis=1)

def severity_to_color(s):
    if s >= 10: return [255, 0, 0, 230]
    elif s >= 5: return [255, 60, 60, 210]
    elif s >= 2: return [255, 100, 100, 180]
    elif s > 0: return [255, 160, 160, 150]
    else: return [200, 200, 200, 100]

df["color"] = df["sev_score"].apply(severity_to_color)

# -------------------------
# 지도 보기
# -------------------------
if mode == "지도 보기":
    st.title("🗺️ 사고다발지역 지도")

    if not has_latlon:
        st.error("위도/경도 컬럼이 필요합니다.")
    else:
        center_lat = float(df["위도"].mean())
        center_lon = float(df["경도"].mean())

        layers = []

        # 대한민국 윤곽선 Layer 추가
        if korea_geo:
            layers.append(
                pdk.Layer(
                    "GeoJsonLayer",
                    data=korea_geo,
                    stroked=True,
                    filled=False,
                    get_line_color=[80, 80, 80],
                    line_width_min_pixels=1.5
                )
            )

        # 사고 분포 Layer
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position=["경도","위도"],
                get_color="color",
                get_radius=90,
                pickable=True
            )
        )

        # 사고 심각도 Heatmap
        layers.append(
            pdk.Layer(
                "HeatmapLayer",
                data=df,
                get_position=["경도","위도"],
                aggregation="SUM",
                weight="sev_score",
                radiusPixels=80,
                intensity=2,
                threshold=0.05
            )
        )

        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=6.5)
        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=view_state,
            layers=layers,
            tooltip={
                "html": "<b>{사고지역위치명}</b><br/>사고건수: {사고건수} / 사상자: {사상자수}",
                "style": {"color": "white", "background-color": "rgba(0,0,0,0.7)"}
            }
        )
        st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# 통계 보기
# -------------------------
elif mode == "통계 보기":
    st.title("📊 사고 통계 분석")

    stat_type = st.selectbox(
        "보고 싶은 통계 유형 선택 👇",
        ["사고건수 상위 지역", "사고유형 비율", "연도별 추이", "사망자수/부상자수 비교"]
    )

    if stat_type == "사고건수 상위 지역" and "사고다발지역시도시군구" in df.columns:
        by_dist = df.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수",
                     title="사고건수 상위 지역 Top 15", color="사고건수",
                     color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True)

    elif stat_type == "사고유형 비율" and type_col:
        by_type = df.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율",
                     color_discrete_sequence=px.colors.sequential.Reds)
        st.plotly_chart(fig, use_container_width=True)

    elif stat_type == "연도별 추이" and year_col:
        by_year = df.groupby(year_col)["사고건수"].sum().reset_index()
        fig = px.line(by_year, x=year_col, y="사고건수", title="연도별 사고 발생 추이", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    elif stat_type == "사망자수/부상자수 비교":
        cols = [c for c in ["사망자수","중상자수","경상자수"] if c in df.columns]
        if cols:
            melted = df[cols].sum().reset_index()
            melted.columns = ["유형", "인원수"]
            fig = px.bar(melted, x="유형", y="인원수", title="사망자/부상자 비교",
                         color="유형", color_discrete_sequence=px.colors.sequential.Reds)
            st.plotly_chart(fig, use_container_width=True)
