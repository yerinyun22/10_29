import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="패턴 관찰기 | Yerin’s Pink Pattern",
    page_icon="🌸",
    layout="wide"
)

# --- 스타일링 ---
st.markdown("""
<style>
body { 
    background: linear-gradient(to right, #ffe6f0, #f9d6ff); 
    color: #333; 
    font-family: 'Pretendard', sans-serif; 
}
h1, h2, h3 { text-align: center; }
.stButton>button {
    background: linear-gradient(90deg, #f783ac, #f5a3d1);
    color: white;
    border: none;
    padding: 0.7em 1.5em;
    border-radius: 12px;
    font-weight: 600;
    transition: 0.3s;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #f5a3d1, #f783ac);
    transform: scale(1.05);
}
</style>
""", unsafe_allow_html=True)

# --- 타이틀 ---
st.title("🌸 패턴 관찰기")
st.markdown("#### 하루의 감정과 집중을 핑크빛 그라데이션으로 기록해보세요. 하나의 예술 작품이 됩니다.")

# --- 감정 입력 ---
st.subheader("1️⃣ 오늘의 감정 기록")
mood = st.selectbox("지금의 감정을 고르세요.", 
                    ["😊 평온", "💖 설렘", "🌸 희망", "🔥 집중", "💭 혼란", "💤 피곤", "💔 슬픔", "🌿 차분"])
intensity = st.slider("집중도 (0~10)", 0, 10, 5)
time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- 감정 색상 매핑 ---
color_map = {
    "😊 평온": "#ffcce6", "💖 설렘": "#ff99cc", "🌸 희망": "#ffb3d9",
    "🔥 집중": "#ff4d94", "💭 혼란": "#e6cce6", "💤 피곤": "#ffd6e6",
    "💔 슬픔": "#ffb3cc", "🌿 차분": "#ffcce6"
}
color = color_map.get(mood, "#ffcce6")

# --- 데이터 저장 ---
if "data" not in st.session_state:
    st.session_state["data"] = pd.DataFrame(columns=["time", "mood", "intensity", "color"])

if st.button("🌷 감정 기록하기"):
    new_entry = pd.DataFrame([[time_now, mood, intensity, color]], columns=["time", "mood", "intensity", "color"])
    st.session_state["data"] = pd.concat([st.session_state["data"], new_entry], ignore_index=True)
    st.success("오늘의 감정이 기록되었습니다!")

# --- 시각화 (Streamlit만 사용, matplotlib 없이) ---
if len(st.session_state["data"]) > 0:
    st.subheader("2️⃣ 오늘의 감정 패턴")
    df = st.session_state["data"]

    # 색상 블록을 Streamlit columns로 시각화
    cols = st.columns(len(df))
    for i, row in enumerate(df.itertuples()):
        with cols[i]:
            st.markdown(f"""
            <div style="
                background:{row.color};
                height:80px;
                border-radius:8px;
                margin-bottom:4px;
                display:flex;
                align-items:center;
                justify-content:center;
                color:white;
                font-weight:bold;
            ">
            {row.mood} {row.intensity}
            </div>
            """, unsafe_allow_html=True)

    # --- 감정 기록 카드 ---
    st.markdown("#### 📊 감정 기록 카드")
    for row in df.itertuples():
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:6px;">
            <div style="width:30px; height:30px; background:{row.color}; border-radius:50%; margin-right:10px;"></div>
            <div style="font-size:16px;">{row.time} — {row.mood} — 집중도 {row.intensity}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
---
💡 하루 3번만 기록해도 충분합니다.  
시간이 쌓이면, 당신의 하루가 한 폭의 핑크빛 예술 작품이 됩니다.
""")
