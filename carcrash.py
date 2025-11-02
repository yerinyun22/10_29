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

# -------------------------
# 스타일 적용: 전체 흰 배경, 검은 글씨
# -------------------------
st.markdown("""
<style>
body { background-color: white; color: black; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# 유틸: Haversine 거리 계산
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
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
    a = np.sin(dlat / 2)**2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# -------------------------
# 데이터 로드 (Google Drive 링크)
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
# 기본 체크
# -------------------------
has_latlon = {"위도", "경도"}.issubset(set(data.columns))
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None
severity_related_cols = set(["사망자수", "중상자수", "경상자수", "사고건수", "사상자수"]) & set(data.columns)

# -------------------------
# 사이드바: 필터
# -------------------------
st.sidebar.header("🔎 필터 · 검색 / 안전경로")

# 연도 범위 선택
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

# 사고유형 선택
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
st.markdown("사고 데이터 기반 **히트맵/클러스터** 시각화 및 **안전경로 후보 생성**")

# -------------------------
# 지도 설정
# -------------------------
if not has_latlon:
    st.error("위도/경도 컬럼이 필요합니다.")
else:
    center_lat = float(df["위도"].mean())
    center_lon = float(df["경도"].mean())

    # 확대/축소 버튼
    zoom_level = st.sidebar.slider("지도 확대/축소", min_value=5, max_value=15, value=6)

    layers = [
        pdk.Layer(
            "HeatmapLayer",
            data=df,
            get_position=["경도","위도"],
            aggregation="SUM",
            weight="sev_score",
            radiusPixels=60
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["경도","위도"],
            get_color="color",
            get_radius=60,
            pickable=True
        )
    ]

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom_level)
    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html":"<b>{사고지역위치명}</b><br/>사고건수: {사고건수} / 사상자: {사상자수}",
            "style":{"color":"black"}  # 검은 글씨
        }
    )

    st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# 통계
# -------------------------
st.subheader("📊 통계")
if "사고다발지역시도시군구" in df.columns and "사고건수" in df.columns:
    by_dist = df.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수", title="구별 사고건수 Top 15")
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font_color='black'
    )
    st.plotly_chart(fig, use_container_width=True)

if type_col and "사고건수" in df.columns:
    by_type = df.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig2 = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율")
    fig2.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font_color='black'
    )
    st.plotly_chart(fig2, use_container_width=True)
