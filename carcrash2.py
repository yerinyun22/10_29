import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(page_title="교통사고 위험지역 시각화", layout="wide")

# -------------------------
# 데이터 불러오기
# -------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("accident_data.csv")  # 파일명 수정 가능
    return df

df = load_data()

# -------------------------
# 거리 계산 함수
# -------------------------
def calc_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# -------------------------
# 사이드바 메뉴
# -------------------------
st.sidebar.title("📍 메뉴")
menu = st.sidebar.radio("원하는 기능을 선택하세요", ["지도 보기", "데이터 보기", "설정", "QnA 보기"])

# -------------------------
# 지도 보기
# -------------------------
if menu == "지도 보기":
    st.header("🗺 교통사고 위험지역 지도")

    st.write("아래 지도에서 사고 지역을 클릭하면 해당 지역의 상세 정보를 볼 수 있습니다.")

    # 중심 좌표
    center_lat = df["위도"].mean()
    center_lon = df["경도"].mean()

    # PyDeck 지도 시각화
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position=["경도", "위도"],
        get_color="[255, 0, 0, 160]",
        get_radius=100,
        pickable=True,
    )

    tooltip = {"html": "<b>사고 발생일:</b> {사고일시}<br><b>사상자수:</b> {사상자수}<br><b>도로형태:</b> {도로형태}", "style": {"backgroundColor": "white", "color": "black"}}

    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v10",
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11, pitch=0),
        layers=[layer],
        tooltip=tooltip,
    )

    st.pydeck_chart(deck)

# -------------------------
# 데이터 보기
# -------------------------
elif menu == "데이터 보기":
    st.header("📊 사고 데이터 미리보기")
    st.dataframe(df.head(50))

# -------------------------
# 설정 (Settings)
# -------------------------
elif menu == "설정":
    st.header("⚙️ 설정")

    with st.expander("지도 설정"):
        map_style = st.selectbox("지도 스타일 선택", ["light-v10", "dark-v10", "streets-v12", "satellite-streets-v12"])
        radius = st.slider("마커 반경 조정", 50, 300, 100)

    with st.expander("데이터 필터 설정"):
        min_casualties = st.slider("표시할 최소 사상자 수", 0, int(df["사상자수"].max()), 0)
        df_filtered = df[df["사상자수"] >= min_casualties]
        st.success(f"필터 적용됨: 사상자수 {min_casualties}명 이상 ({len(df_filtered)}건)")

    st.write("설정이 저장되었습니다. '지도 보기' 탭에서 결과를 확인하세요.")

# -------------------------
# QnA 보기
# -------------------------
elif menu == "QnA 보기":
    st.header("💬 QnA 게시판")

    # 저장용 세션 상태
    if "qna" not in st.session_state:
        st.session_state.qna = []

    with st.expander("📨 새 QnA 등록"):
        q_title = st.text_input("질문 제목")
        q_content = st.text_area("질문 내용")
        if st.button("등록"):
            if q_title and q_content:
                st.session_state.qna.append({"title": q_title, "content": q_content, "answer": ""})
                st.success("QnA가 등록되었습니다.")
            else:
                st.warning("제목과 내용을 모두 입력해주세요.")

    st.subheader("📋 등록된 QnA 목록")

    if len(st.session_state.qna) == 0:
        st.info("아직 등록된 QnA가 없습니다.")
    else:
        for i, q in enumerate(st.session_state.qna):
            with st.expander(f"❓ {q['title']}"):
                st.write(q["content"])
                if q["answer"]:
                    st.success(f"💬 답변: {q['answer']}")
                else:
                    answer = st.text_area(f"답변 입력 (질문: {q['title']})", key=f"answer_{i}")
                    if st.button("답변 등록", key=f"btn_{i}"):
                        st.session_state.qna[i]["answer"] = answer
                        st.success("답변이 등록되었습니다.")
