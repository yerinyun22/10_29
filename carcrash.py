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
# 기본 체크
# -------------------------
has_latlon = {"위도", "경도"}.issubset(set(data.columns))
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None

# -------------------------
# 앱 모드 선택 (지도 / 통계)
# -------------------------
mode = st.sidebar.radio("화면 선택", ["지도 보기", "통계 보기"])

# -------------------------
# 지도 필터 (지도 모드 전용)
# -------------------------
if mode == "지도 보기":
    st.title("🛡️ 사고다발지역 안전지도 - 지도 화면")

    df_map = data.copy()

    # 연도 필터
    if year_col:
        years = sorted(df_map[year_col].dropna().unique().astype(int))
        sel_year_range = st.sidebar.slider(
            "연도 범위 선택",
            min_value=int(min(years)),
            max_value=int(max(years)),
            value=(int(min(years)), int(max(years)))
        )
        df_map = df_map[(df_map[year_col] >= sel_year_range[0]) & (df_map[year_col] <= sel_year_range[1])]

    # 사고유형 필터
    if type_col:
        types = sorted(df_map[type_col].dropna().unique())
        sel_types = st.sidebar.multiselect("사고유형 필터", options=types, default=types)
        df_map = df_map[df_map[type_col].isin(sel_types)]

    # 심각도 계산
    def severity_score(row):
        score = 0.0
        if "사망자수" in row.index: score += 10.0 * (row.get("사망자수",0) or 0)
        if "중상자수" in row.index: score += 3.0 * (row.get("중상자수",0) or 0)
        if "경상자수" in row.index: score += 1.0 * (row.get("경상자수",0) or 0)
        if "사고건수" in row.index: score += 0.5 * (row.get("사고건수",0) or 0)
        return score

    df_map["sev_score"] = df_map.apply(severity_score, axis=1)

    def severity_to_color(s):
        if s >= 10: return [180,0,0,200]
        elif s >=5: return [230,40,40,180]
        elif s >=2: return [255,140,0,150]
        elif s >0: return [255,210,0,130]
        else: return [150,150,150,90]

    df_map["color"] = df_map["sev_score"].apply(severity_to_color)

    # 지도 중심
    center_lat = float(df_map["위도"].mean())
    center_lon = float(df_map["경도"].mean())

    # 지도 확대/축소 버튼 (지도 위에만)
    zoom_level = st.slider("지도 확대/축소", min_value=5, max_value=15, value=6)

    layers = [
        pdk.Layer(
            "HeatmapLayer",
            data=df_map,
            get_position=["경도","위도"],
            aggregation="SUM",
            weight="sev_score",
            radiusPixels=60
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
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
            "style":{"color":"black"}
        }
    )

    st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# 통계 모드
# -------------------------
else:
    st.title("📊 사고 통계 화면")

    df_stats = data.copy()

    # 통계에서도 연도 필터
    if year_col:
        years = sorted(df_stats[year_col].dropna().unique().astype(int))
        sel_year_range = st.sidebar.slider(
            "연도 범위 선택 (통계용)",
            min_value=int(min(years)),
            max_value=int(max(years)),
            value=(int(min(years)), int(max(years)))
        )
        df_stats = df_stats[(df_stats[year_col] >= sel_year_range[0]) & (df_stats[year_col] <= sel_year_range[1])]

    # 통계에서도 사고유형 필터
    if type_col:
        types = sorted(df_stats[type_col].dropna().unique())
        sel_types = st.sidebar.multiselect("사고유형 필터 (통계용)", options=types, default=types)
        df_stats = df_stats[df_stats[type_col].isin(sel_types)]

    # 구별 사고건수 Top 15
    if "사고다발지역시도시군구" in df_stats.columns and "사고건수" in df_stats.columns:
        by_dist = df_stats.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(
            by_dist.head(15),
            x="사고다발지역시도시군구",
            y="사고건수",
            title="구별 사고건수 Top 15",
            text="사고건수"
        )
        fig.update_traces(
            textposition="outside",
            textfont_color="black"
        )
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font_color='black'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 사고유형별 비율
    if type_col and "사고건수" in df_stats.columns:
        by_type = df_stats.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig2 = px.pie(
            by_type,
            values="사고건수",
            names=type_col,
            title="사고유형별 비율"
        )
        fig2.update_traces(
            textinfo="percent+label",
            textfont_size=14,
            textfont_color="black"
        )
        fig2.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font_color='black'
        )
        st.plotly_chart(fig2, use_container_width=True)
