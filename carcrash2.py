import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(page_title="교통사고 위험지도", page_icon="🚦", layout="wide")

# -------------------------
# 데이터 불러오기 (예시)
# -------------------------
@st.cache_data
def load_data():
    data = pd.DataFrame({
        '위도': [37.5665, 37.5665, 37.5651, 37.5700, 37.5700],
        '경도': [126.9780, 126.9780, 126.9900, 126.9820, 126.9820],
        '사고유형': ['차대사람', '차대차', '차대차', '차량단독', '차대사람'],
        '사망자수': [0, 1, 1, 0, 0],
        '부상자수': [2, 3, 1, 1, 4],
        '발생일시': ['2025-10-01', '2025-10-02', '2025-10-03', '2025-10-04', '2025-10-05']
    })
    return data

data = load_data()

# -------------------------
# 사이드바 메뉴
# -------------------------
menu = st.sidebar.selectbox(
    "📍 메뉴 선택",
    ["사고 지도 보기", "데이터 분석", "QnA 보기"]
)

# -------------------------
# 상단 설정 버튼
# -------------------------
with st.sidebar.expander("⚙️ 설정", expanded=False):
    st.write("아래 설정을 조정하세요.")
    map_style = st.selectbox("지도 스타일", ["light", "dark", "streets", "satellite"])
    show_data = st.checkbox("지도 아래 데이터표 보기", value=True)
    st.write("---")
    st.write("기타 설정")
    enable_filter = st.checkbox("데이터 필터 기능 사용", value=True)
    st.caption("필터 사용 시 조건에 맞는 사고만 표시됩니다.")


# -------------------------
# 지도 화면
# -------------------------
if menu == "사고 지도 보기":
    st.title("🚦 교통사고 위험 지도")

    # 필터 적용
    if enable_filter:
        st.subheader("🔍 데이터 필터")
        accident_type = st.multiselect("사고 유형 선택", data["사고유형"].unique(), default=data["사고유형"].unique())
        filtered = data[data["사고유형"].isin(accident_type)]
    else:
        filtered = data

    # 동일 지역 사고를 하나로 합치기
    grouped = (
        filtered.groupby(['위도', '경도'])
        .agg({
            '사고유형': lambda x: ', '.join(sorted(set(x))),
            '사망자수': 'sum',
            '부상자수': 'sum',
            '발생일시': lambda x: ', '.join(sorted(set(x)))
        })
        .reset_index()
    )

    grouped['총사고수'] = filtered.groupby(['위도', '경도']).size().values

    # 지도 표시
    st.pydeck_chart(pdk.Deck(
        map_style=f"mapbox://styles/mapbox/{map_style}-v11",
        initial_view_state=pdk.ViewState(latitude=37.5665, longitude=126.9780, zoom=12),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=grouped,
                get_position='[경도, 위도]',
                get_color='[255, 0, 0, 160]',
                get_radius=100 + grouped['총사고수'] * 40,
                pickable=True
            )
        ],
        tooltip={
            "text": "사고유형: {사고유형}\n총 사고수: {총사고수}\n사망자수: {사망자수}\n부상자수: {부상자수}\n발생일시: {발생일시}"
        }
    ))

    if show_data:
        st.subheader("📋 종합 데이터 미리보기")
        st.dataframe(grouped)


# -------------------------
# 데이터 분석 화면
# -------------------------
elif menu == "데이터 분석":
    st.title("📊 교통사고 데이터 분석")

    st.subheader("사고 유형별 통계")
    fig = px.bar(data, x='사고유형', y='부상자수', color='사고유형', title='사고 유형별 부상자수')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("사고 발생일시별 추세")
    df = data.copy()
    df['발생일시'] = pd.to_datetime(df['발생일시'])
    fig2 = px.line(df, x='발생일시', y='부상자수', title='일자별 부상자 추이')
    st.plotly_chart(fig2, use_container_width=True)


# -------------------------
# QnA 보기 화면
# -------------------------
elif menu == "QnA 보기":
    st.title("💬 QnA 게시판")

    # 기존 QnA 데이터 (임시 예시)
    if "qna" not in st.session_state:
        st.session_state.qna = [
            {"질문": "데이터는 어디서 가져오나요?", "답변": "도로교통공단 공개 데이터셋을 사용합니다."},
            {"질문": "지도 확대가 안 돼요.", "답변": "설정에서 확대 기능을 켤 수 있도록 개선 중입니다."}
        ]

    # QnA 목록 표시
    for i, item in enumerate(st.session_state.qna):
        with st.expander(f"Q{i+1}. {item['질문']}"):
            st.write(f"💬 **답변:** {item['답변']}")

    st.write("---")
    st.subheader("📝 새로운 QnA 추가")

    new_q = st.text_input("질문을 입력하세요:")
    new_a = st.text_area("답변을 입력하세요 (관리자용):")

    if st.button("QnA 추가"):
        if new_q and new_a:
            st.session_state.qna.append({"질문": new_q, "답변": new_a})
            st.success("새로운 QnA가 추가되었습니다!")
        else:
            st.warning("질문과 답변을 모두 입력해주세요.")
