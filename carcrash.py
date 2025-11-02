import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2
import json
import requests

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title="🛡️ 대한민국 안전지도",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# 💡 흰 배경 + 검은 글씨 CSS
# -------------------------
st.markdown("""
<style>
body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
    background-color: white !important;
    color: black !important;
}
[data-testid="stSidebar"] { background-color: #f9f9f9 !important; }
h1, h2, h3, h4, h5, h6, p, label, div, span { color: black !important; }
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
# 메뉴
# -------------------------
menu = st.sidebar.radio("메뉴 선택", ["지도 보기", "통계 보기", "시민 참여"])

# -------------------------
# 공통: 거리 계산
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# -------------------------
# 대한민국 윤곽선 GeoJSON
# -------------------------
geojson_url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/sido.json"
geojson_data = requests.get(geojson_url).json()

# =====================================================
# 1️⃣ 지도 보기
# =====================================================
if menu == "지도 보기":
    st.title("🗺️ 대한민국 사고다발지역 지도")

    # 위도/경도 확인
    if {"위도","경도"}.issubset(data.columns):
        df = data.copy()

        # 심각도 계산
        def severity_score(row):
            score = 0
            if "사망자수" in row: score += 10*(row.get("사망자수",0) or 0)
            if "중상자수" in row: score += 3*(row.get("중상자수",0) or 0)
            if "경상자수" in row: score += 1*(row.get("경상자수",0) or 0)
            if "사고건수" in row: score += 0.5*(row.get("사고건수",0) or 0)
            return score
        df["sev_score"] = df.apply(severity_score, axis=1)

        # 색상
        def sev_color(s):
            if s>=10: return [255,0,0,230]
            elif s>=5: return [255,80,80,200]
            elif s>=2: return [255,150,150,170]
            else: return [255,200,200,140]
        df["color"] = df["sev_score"].apply(sev_color)

        center_lat = float(df["위도"].mean())
        center_lon = float(df["경도"].mean())

        # PyDeck 레이어
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
                get_radius=70,
                pickable=True
            ),
            pdk.Layer(
                "GeoJsonLayer",
                geojson_data,
                stroked=True,
                filled=False,
                get_line_color=[0,0,0,200],
                line_width_min_pixels=2,
                pickable=False
            )
        ]

        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=6)
        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=view_state,
            layers=layers,
            tooltip={"html":"<b>{사고지역위치명}</b><br/>사고건수: {사고건수}<br/>사상자: {사상자수}", 
                     "style":{"color":"white"}}
        )
        st.pydeck_chart(deck, use_container_width=True)

        # 안전 경로 추천
        st.markdown("### 🚗 안전 경로 추천 (예시)")
        st.info("출발지와 목적지를 선택하면 사고율이 낮은 도로를 추천할 수 있도록 확장 예정입니다.")

    else:
        st.error("⚠️ 위도와 경도 컬럼이 필요합니다.")

# =====================================================
# 2️⃣ 통계 보기
# =====================================================
elif menu == "통계 보기":
    st.title("📊 사고 통계 분석")

    # 사고 연도 필터
    year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
    type_col = "사고유형구분" if "사고유형구분" in data.columns else None

    df_stat = data.copy()
    if year_col:
        years = sorted(df_stat[year_col].dropna().unique().astype(int))
        sel_year_range = st.sidebar.slider("연도 범위 선택", min_value=int(min(years)), max_value=int(max(years)), value=(int(min(years)),int(max(years))))
        df_stat = df_stat[(df_stat[year_col]>=sel_year_range[0]) & (df_stat[year_col]<=sel_year_range[1])]

    if type_col:
        types = sorted(df_stat[type_col].dropna().unique())
        sel_types = st.sidebar.multiselect("사고유형 필터", options=types, default=types)
        df_stat = df_stat[df_stat[type_col].isin(sel_types)]

    # 통계 유형 선택
    stat_type = st.selectbox("보고 싶은 통계 유형", ["구별 사고건수 Top 15","사고유형별 비율"])

    if stat_type == "구별 사고건수 Top 15" and "사고다발지역시도시군구" in df_stat.columns and "사고건수" in df_stat.columns:
        by_dist = df_stat.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수", title="구별 사고건수 Top 15")
        st.plotly_chart(fig, use_container_width=True)

    elif stat_type == "사고유형별 비율" and type_col and "사고건수" in df_stat.columns:
        by_type = df_stat.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig2 = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율")
        st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# 3️⃣ 시민 참여
# =====================================================
elif menu == "시민 참여":
    st.title("🙋 시민 참여 공간")

    tab1, tab2, tab3 = st.tabs(["🚨 위험 구역 제보", "🧱 개선 요청 게시판", "🚸 교통안전 캠페인 참여"])

    with tab1:
        st.subheader("🚨 위험 구역 제보하기")
        region = st.text_input("📍 위치 또는 지역명")
        issue_type = st.selectbox("🚧 문제 유형", ["신호등 고장","가로등 부족","횡단보도 없음","도로 파손","기타"])
        detail = st.text_area("📝 상세 설명")
        if st.button("제보 제출"):
            st.success("✅ 제보가 접수되었습니다. 검토 후 지도에 반영됩니다.")

    with tab2:
        st.subheader("🧱 지역 개선 요청 게시판")
        title = st.text_input("제목")
        content = st.text_area("내용")
        if st.button("요청 등록"):
            st.success("✅ 요청이 등록되었습니다. 담당 기관에 전달됩니다.")

    with tab3:
        st.subheader("🚸 교통안전 캠페인 참여")
        choice = st.radio("캠페인 선택", ["보행자 우선 캠페인","음주운전 근절 서약","안전벨트 착용 인증"])
        if st.button("참여하기"):
            st.success(f"🎉 '{choice}' 캠페인에 참여해주셔서 감사합니다!")
