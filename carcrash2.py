import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(
    page_title="🛡️ 대한민국 안전지도",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# 흰 배경 + 검은 글씨 스타일
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
        # 심각도 계산
        def severity_score(row):
            score = 0
            if "사망자수" in row: score += 10 * (row["사망자수"] or 0)
            if "중상자수" in row: score += 3 * (row["중상자수"] or 0)
            if "경상자수" in row: score += 1 * (row["경상자수"] or 0)
            if "사고건수" in row: score += 0.5 * (row["사고건수"] or 0)
            return score

        df["sev_score"] = df.apply(severity_score, axis=1)

        # 색상
        def severity_to_color(s):
            if s >= 10: return [255, 0, 0, 230]
            elif s >= 5: return [255, 80, 80, 200]
            elif s >= 2: return [255, 150, 150, 170]
            else: return [255, 200, 200, 140]

        df["color"] = df["sev_score"].apply(severity_to_color)
        center_lat = float(df["위도"].mean())
        center_lon = float(df["경도"].mean())

        # **줌 레벨 선택**
        zoom_level = st.slider("지도 확대 수준 선택 (줌 레벨)", 4, 12, 6)

        # **줌에 따라 표시 데이터 필터링**
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
            map_style="mapbox://styles/mapbox/light-v9",
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
# 통계 보기
# -------------------------
elif menu == "통계 보기":
    st.title("📊 사고 통계 분석")
    stat_type = st.selectbox("보고 싶은 통계 유형 선택", ["구별 사고건수", "사고유형별 비율"])
    
    if stat_type == "구별 사고건수" and "사고다발지역시도시군구" in df.columns:
        by_dist = df.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수", title="구별 사고건수 Top 15",
                     color_discrete_sequence=["crimson"])
        st.plotly_chart(fig, use_container_width=True)
    
    elif stat_type == "사고유형별 비율" and type_col:
        by_type = df.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig2 = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율",
                      color_discrete_sequence=px.colors.sequential.Reds)
        st.plotly_chart(fig2, use_container_width=True)

# -------------------------
# 시민 참여
# -------------------------
elif menu == "시민 참여":
    st.title("🙋 시민 참여 공간")
    tab1, tab2, tab3 = st.tabs(["🚨 위험 구역 제보", "🧱 개선 요청 게시판", "🚸 교통안전 캠페인 참여"])
    
    with tab1:
        st.subheader("🚨 위험 구역 제보")
        region = st.text_input("📍 위치/지역명")
        issue_type = st.selectbox("🚧 문제 유형", ["신호등 고장","가로등 부족","횡단보도 없음","도로 파손","기타"])
        detail = st.text_area("📝 상세 설명")
        if st.button("제보 제출"):
            st.success("✅ 제보가 접수되었습니다.")

    with tab2:
        st.subheader("🧱 개선 요청 게시판")
        title = st.text_input("제목")
        content = st.text_area("내용")
        if st.button("요청 등록"):
            st.success("✅ 요청이 등록되었습니다.")

    with tab3:
        st.subheader("🚸 교통안전 캠페인 참여")
        choice = st.radio("캠페인 선택", ["보행자 우선 캠페인","음주운전 근절 서약","안전벨트 착용 인증"])
        if st.button("참여하기"):
            st.success("✅ 참여 완료!")
