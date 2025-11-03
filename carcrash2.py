import streamlit as st
import pandas as pd
import pydeck as pdk
import os

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(page_title="교통사고 위험지역 시각화", layout="wide")

# -------------------------
# 데이터 로드 (샘플용)
# -------------------------
@st.cache_data
def load_data():
    data = pd.DataFrame({
        '위도': [37.5665, 37.5651, 37.5700],
        '경도': [126.9780, 126.9900, 126.9750],
        '사고건수': [5, 3, 8],
        '지역명': ['시청역', '을지로입구', '광화문']
    })
    return data

data = load_data()

# -------------------------
# QnA 저장용 CSV 파일
# -------------------------
qna_file = "qna_data.csv"

if not os.path.exists(qna_file):
    qna_df = pd.DataFrame(columns=["질문", "답변"])
    qna_df.to_csv(qna_file, index=False, encoding="utf-8-sig")
else:
    qna_df = pd.read_csv(qna_file)

# -------------------------
# 사이드바 메뉴
# -------------------------
menu = st.sidebar.selectbox("메뉴 선택", ["지도 보기", "QnA 보기", "설정"])

# ============================================================
# 1️⃣ 지도 보기
# ============================================================
if menu == "지도 보기":
    st.title("🚦 교통사고 위험지역 시각화")

    st.write("지도에서 사고 다발 지역을 확인하고, 클릭하면 세부 정보를 볼 수 있습니다.")

    layer = pdk.Layer(
        'ScatterplotLayer',
        data=data,
        get_position='[경도, 위도]',
        get_color='[255, 0, 0, 160]',
        get_radius='사고건수 * 50',
        pickable=True
    )

    view_state = pdk.ViewState(
        latitude=37.5665,
        longitude=126.9780,
        zoom=13,
        pitch=0
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>지역명:</b> {지역명}<br/><b>사고건수:</b> {사고건수}",
            "style": {"color": "white"}
        }
    )

    st.pydeck_chart(r)

# ============================================================
# 2️⃣ QnA 보기
# ============================================================
elif menu == "QnA 보기":
    st.title("💬 QnA 게시판")

    tab1, tab2 = st.tabs(["📄 질문 목록", "✏️ 새 질문 등록"])

    # -------------------
    # 질문 목록
    # -------------------
    with tab1:
        st.subheader("📋 등록된 질문들")
        qna_df = pd.read_csv(qna_file)

        if len(qna_df) == 0:
            st.info("등록된 질문이 없습니다.")
        else:
            for i, row in qna_df.iterrows():
                with st.expander(f"Q{i+1}. {row['질문']}"):
                    st.write(f"**답변:** {row['답변'] if pd.notna(row['답변']) and row['답변'].strip() != '' else '아직 답변이 없습니다.'}")

                    new_answer = st.text_area(f"답변 입력 (Q{i+1})", value=row['답변'] if pd.notna(row['답변']) else "")
                    if st.button(f"💾 답변 저장 (Q{i+1})"):
                        qna_df.at[i, '답변'] = new_answer
                        qna_df.to_csv(qna_file, index=False, encoding="utf-8-sig")
                        st.success("답변이 저장되었습니다.")
                        st.rerun()

    # -------------------
    # 새 질문 등록
    # -------------------
    with tab2:
        st.subheader("✏️ 새로운 질문 등록")

        new_question = st.text_area("질문 내용을 입력하세요")

        if st.button("📤 질문 등록"):
            if new_question.strip() == "":
                st.warning("질문 내용을 입력해야 합니다.")
            else:
                new_row = pd.DataFrame([[new_question, ""]], columns=["질문", "답변"])
                qna_df = pd.concat([qna_df, new_row], ignore_index=True)
                qna_df.to_csv(qna_file, index=False, encoding="utf-8-sig")
                st.success("질문이 등록되었습니다.")
                st.rerun()

# ============================================================
# 3️⃣ 설정
# ============================================================
elif menu == "설정":
    st.title("⚙️ 지도 설정")

    map_style = st.selectbox(
        "지도 스타일 선택",
        ["light", "dark", "streets", "satellite"]
    )

    st.write(f"현재 선택된 지도 스타일: `{map_style}`")

    st.info("이 기능은 이후 지도 표시 시 적용될 예정입니다.")
