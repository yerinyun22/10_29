import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# 페이지 기본 설정
# -------------------------
st.set_page_config(page_title="교통사고 위험지역 시각화", layout="wide")

# -------------------------
# 데이터 불러오기
# -------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("accident_data.csv")  # 교통사고 데이터 파일 경로
    return df

data = load_data()

# -------------------------
# 지도 표시 함수
# -------------------------
def show_map():
    st.subheader("🚗 교통사고 위험지역 지도")

    # 지도 중심좌표 계산
    center_lat = data["위도"].mean()
    center_lon = data["경도"].mean()

    # Pydeck 지도 설정
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["경도", "위도"],
        get_color=[255, 0, 0, 150],
        get_radius=80,
        pickable=True,
    )

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "사고 유형: {사고유형}\n사상자수: {사상자수}"}
    )

    st.pydeck_chart(deck)

    # 클릭 시 관련 데이터 표시
    st.info("지도를 클릭하면 사고 관련 정보가 표시됩니다.")
    st.dataframe(data.head(10))

# -------------------------
# 데이터 보기 함수
# -------------------------
def show_data():
    st.subheader("📊 교통사고 데이터 보기")
    with st.expander("데이터 미리보기"):
        st.dataframe(data.head(20))

    # 간단한 통계 시각화
    if "사고유형" in data.columns:
        fig = px.histogram(data, x="사고유형", title="사고 유형별 빈도")
        st.plotly_chart(fig)

# -------------------------
# QnA 보기 (새 메뉴)
# -------------------------
def show_qna():
    st.subheader("💬 QnA 게시판")

    if "qna" not in st.session_state:
        st.session_state.qna = []

    # 기존 질문 리스트
    if st.session_state.qna:
        for i, (q, a) in enumerate(st.session_state.qna):
            with st.expander(f"Q{i+1}: {q}"):
                if a:
                    st.write(f"**답변:** {a}")
                else:
                    new_answer = st.text_area(f"답변 입력 (Q{i+1})", key=f"ans_{i}")
                    if st.button(f"답변 등록 (Q{i+1})"):
                        st.session_state.qna[i] = (q, new_answer)
                        st.success("✅ 답변이 등록되었습니다.")
                        st.experimental_rerun()
    else:
        st.info("등록된 질문이 없습니다.")

    # 새 질문 등록
    st.markdown("---")
    new_q = st.text_input("새 질문 등록")
    if st.button("질문 추가"):
        if new_q:
            st.session_state.qna.append((new_q, None))
            st.success("✅ 질문이 추가되었습니다.")
            st.experimental_rerun()
        else:
            st.warning("질문 내용을 입력해주세요.")

# -------------------------
# 설정 페이지
# -------------------------
def show_settings():
    st.subheader("⚙️ 설정")
    st.text("이곳에서 지도 및 데이터 관련 기본 설정을 변경할 수 있습니다.")
    mapbox_api = st.text_input("Mapbox API Key 입력", type="password")
    st.checkbox("지도 마커 강조", value=True)
    st.checkbox("데이터 자동 새로고침", value=False)

# -------------------------
# 사이드바 메뉴
# -------------------------
menu = st.sidebar.radio(
    "메뉴 선택",
    ["지도 보기", "데이터 보기", "QnA 보기", "설정"]
)

# -------------------------
# 메뉴별 페이지 표시
# -------------------------
if menu == "지도 보기":
    show_map()
elif menu == "데이터 보기":
    show_data()
elif menu == "QnA 보기":
    show_qna()
elif menu == "설정":
    show_settings()
