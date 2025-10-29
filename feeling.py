import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

st.set_page_config(page_title="패턴 관찰기 | Yerin’s Pattern Observer", 
                   page_icon="🌈", layout="wide")

# --- 스타일링 ---
st.markdown("""
<style>
body { background: linear-gradient(to right, #f5f7fa, #c3cfe2); color: #333; font-family: 'Pretendard', sans-serif; }
h1, h2, h3 { text-align: center; }
.stButton>button {
    background: linear-gradient(90deg, #a5b4fc, #c084fc);
    color: white;
    border: none;
    padding: 0.7em 1.5em;
    border-radius: 12px;
    font-weight: 600;
    transition: 0.3s;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #c084fc, #a5b4fc);
    transform: scale(1.05);
}
.stSlider>div>div>div>div { color: #555; }
</style>
""", unsafe_allow_html=True)

# --- 타이틀 ---
st.title("🌙 패턴 관찰기 (Pattern Observer)")
st.markdown("#### 하루의 감정과 집중을 색으로 남겨보세요. 기록이 모이면 하나의 예술 작품이 됩니다.")

# --- 감정 입력 ---
st.subheader("1️⃣ 오늘의 감정 기록")
mood = st.selectbox("지금의 감정을 고르세요.", 
                    ["😊 평온", "🌿 차분", "🔥 집중", "💭 혼란", "💤 피곤", "🌈 희망", "💔 슬픔", "💫 설렘"])
intensity = st.slider("집중도 (0~10)", 0, 10, 5)
time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

color_map = {
    "😊 평온": "#a5d8ff", "🌿 차분": "#c3fae8", "🔥 집중": "#ff6b6b",
    "💭 혼란": "#dee2e6", "💤 피곤": "#ced4da", "🌈 희망": "#ffd43b",
    "💔 슬픔": "#74c0fc", "💫 설렘": "#f783ac"
}
color = color_map.get(mood, "#ccc")

# --- 데이터 저장 ---
if "data" not in st.session_state:
    st.session_state["data"] = pd.DataFrame(columns=["time", "mood", "intensity", "color"])

if st.button("🪞 감정 기록하기"):
    new_entry = pd.DataFrame([[time_now, mood, intensity, color]], columns=["time", "mood", "intensity", "color"])
    st.session_state["data"] = pd.concat([st.session_state["data"], new_entry], ignore_index=True)
    st.success("오늘의 감정이 기록되었습니다 🌷")

# --- 시각화 ---
if len(st.session_state["data"]) > 0:
    st.subheader("2️⃣ 오늘의 감정 패턴 (아트워크)")
    df = st.session_state["data"]

    fig, ax = plt.subplots(figsize=(10, 2))
    colors = df["color"].tolist()
    # 그라데이션으로 자연스럽게 연결
    for i, c in enumerate(colors):
        ax.barh(0, 1, left=i, color=c, edgecolor='white', height=0.7)
        if i > 0:
            # 부드러운 블렌드 느낌
            blend = np.linspace(0,1,50)
            for j,b in enumerate(blend):
                ax.barh(0, 1/50, left=i-1+j/50, color=c, edgecolor='white', height=0.7, alpha=b*0.3)

    ax.set_xlim(0, len(df))
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_facecolor("#f0f4f8")
    ax.set_title("오늘의 감정 그라데이션", fontsize=16, fontweight='bold')
    st.pyplot(fig)

    # --- 감정 카드로 요약 ---
    st.markdown("#### 📊 감정 기록 카드")
    for i, row in df.iterrows():
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <div style="width:30px; height:30px; background:{row['color']}; border-radius:50%; margin-right:10px;"></div>
            <div style="font-size:16px;">{row['time']} — {row['mood']} — 집중도 {row['intensity']}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
---
💡 **Tip**: 하루 3번만 기록해도 충분합니다.  
시간이 쌓이면, 당신의 하루가 한 폭의 디지털 예술 작품으로 완성됩니다.
""")
