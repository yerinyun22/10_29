import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import re
import time

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title="🛡️ 대한민국 안전지도",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# ⚙️ 설정 (접이식 Expander)
# -------------------------
with st.sidebar.expander("⚙️ 설정 열기 / 닫기"):
    st.markdown("### 사용자 설정")

    # 글씨 크기
    font_size = st.slider("글씨 크기 조정", 12, 30, 16)

    # 글씨 색상
    font_color = st.color_picker("글씨 색상 선택", "#000000")

    # 밝기 설정
    theme = st.radio("밝기 조정", ["밝음 모드", "어두움 모드"])
    bg_color = "#ffffff" if theme == "밝음 모드" else "#1e1e1e"
    text_color = font_color if theme == "밝음 모드" else "#f1f1f1"

    # 현재 날짜와 시간 실시간 표시
    st.markdown("🕒 현재 시각:")
    time_placeholder = st.empty()

    # Q&A 질문
    st.markdown("---")
    st.markdown("### ❓ Q&A 질문")
    user_question = st.text_area("궁금한 점을 입력하세요")
    if st.button("질문 제출"):
        st.success("✅ 질문이 접수되었습니다!")

# -------------------------
# 스타일 적용
# -------------------------
st.markdown(f"""
<style>
body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {{
    background-color: {bg_color} !important;
    color: {text_color} !important;
    font-size: {font_size}px !important;
}}
h1, h2, h3, h4, h5, h6, p, label, div {{
    color: {text_color} !important;
    font-size: {font_size}px !important;
}}
[data-testid="stSidebar"] {{
    background-color: {'#f9f9f9' if theme == '밝음 모드' else '#2e2e2e'} !important;
}}
</style>
""", unsafe_allow_html=True)

# -------------------------
# 거리 계산
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
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
# 메뉴 선택
# -------------------------
menu = st.sidebar.radio("메뉴 선택", ["지도 보기", "통계 보기", "시민 참여"])

# -------------------------
# 공통 필터
# -------------------------
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None

if year_col:
    years = sorted(data[year_col].dropna().unique().astype(int))
    sel_year_range = st.sidebar.slider("연도 범위 선택", min_value=min(years), max_value=max(years),
                                       value=(min(years), max(years)))
else:
    sel_year_range = None

if type_col:
    types = sorted(data[type_col].dropna().unique())
    sel_types = st.sidebar.multiselect("사고유형 필터", options=types, default=types)
else:
    sel_types = None

df = data.copy()
if sel_year_range and year_col:
    df = df[(df[year_col] >= sel_year_range[0]) & (df[year_col] <= sel_year_range[1])]
if sel_types and type_col:
    df = df[df[type_col].isin(sel_types)]

# -------------------------
# 지도 보기
# -------------------------
if menu == "지도 보기":
    st.title("🗺️ 대한민국 사고다발지역 지도")

    has_latlon = {"위도","경도"}.issubset(df.columns)
    if not has_latlon:
        st.error("⚠️ 위도와 경도 컬럼이 필요합니다.")
    else:
        def severity_score(row):
            score = 0
            if "사망자수" in row: score += 10 * (row["사망자수"] or 0)
            if "중상자수" in row: score += 3 * (row["중상자수"] or 0)
            if "경상자수" in row: score += 1 * (row["경상자수"] or 0)
            if "사고건수" in row: score += 0.5 * (row["사고건수"] or 0)
            return score

        df["sev_score"] = df.apply(severity_score, axis=1)

        def severity_to_color(s):
            if s >= 10: return [255, 0, 0, 230]
            elif s >= 5: return [255, 80, 80, 200]
            elif s >= 2: return [255, 150, 150, 170]
            else: return [255, 200, 200, 140]

        df["color"] = df["sev_score"].apply(severity_to_color)
        center_lat = float(df["위도"].mean())
        center_lon = float(df["경도"].mean())

        zoom_level = st.slider("지도 확대 수준 선택 (줌 레벨)", 4, 12, 6)

        if zoom_level <= 6:
            df_plot = df[df["sev_score"] >= 5]
        elif zoom_level <= 9:
            df_plot = df[df["sev_score"] >= 2]
        else:
            df_plot = df.copy()

        layers = [
            pdk.Layer(
                "HeatmapLayer",
                data=df_plot,
                get_position=["경도","위도"],
                aggregation="SUM",
                weight="sev_score",
                radiusPixels=60
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=df_plot,
                get_position=["경도","위도"],
                get_color="color",
                get_radius=70,
                pickable=True
            )
        ]

        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9" if theme == "밝음 모드" else "mapbox://styles/mapbox/dark-v9",
            initial_view_state=pdk.ViewState(
                latitude=center_lat, longitude=center_lon, zoom=zoom_level
            ),
            layers=layers,
            tooltip={"html":"<b>{사고지역위치명}</b><br/>사고건수: {사고건수}<br/>사상자수: {사상자수}",
                     "style":{"color":"white"}}
        )
        st.pydeck_chart(deck, use_container_width=True)

        st.markdown("### 🚗 안전 경로 추천 (예시)")
        st.info("출발지와 목적지를 선택하면 사고율이 낮은 도로를 추천하도록 확장할 수 있습니다.")

# -------------------------
# 통계 보기 (지역명 숫자 제거 및 합산)
# -------------------------
elif menu == "통계 보기":
    st.title("📊 사고 통계 분석")

    # 사고 발생 연도 선택
    if year_col:
        year_list = sorted(df[year_col].dropna().unique().astype(int))
        selected_year = st.selectbox("사고 발생 연도 선택", year_list)
    else:
        selected_year = None

    # 사고 발생 지역 컬럼 탐색
    region_col = None
    for col in ["사고다발지역시도시군구", "시군구", "지역명", "사고지역위치명"]:
        if col in df.columns:
            region_col = col
            break

    if region_col:
        # 숫자 제거하여 동일 지역 통합
        df["region_clean"] = df[region_col].apply(lambda x: re.sub(r"\d+$", "", str(x)).strip())
        regions = sorted(df["region_clean"].dropna().unique())
        selected_region = st.selectbox("사고 발생 지역 선택", regions)
    else:
        selected_region = None

    # 선택 조건으로 필터링
    filtered = df.copy()
    if selected_year and year_col:
        filtered = filtered[filtered[year_col] == selected_year]
    if selected_region and region_col:
        filtered = filtered[filtered["region_clean"] == selected_region]

    # 동일 지역 합산
    if not filtered.empty:
        st.subheader(f"📍 {selected_region} 지역 ({selected_year}년) 사고 통계")
        total_accidents = int(filtered["사고건수"].sum()) if "사고건수" in filtered.columns else len(filtered)
        fatalities = int(filtered["사망자수"].sum()) if "사망자수" in filtered.columns else 0
        injuries = int(filtered["사상자수"].sum()) if "사상자수" in filtered.columns else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("🚗 사고 건수", f"{total_accidents:,}건")
       
