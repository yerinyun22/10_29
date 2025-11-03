import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import datetime

# ---------------------------
# 1️⃣ Mapbox 토큰 불러오기
# ---------------------------
MAPBOX_API_KEY = st.secrets["MAPBOX_API_KEY"]

# ---------------------------
# 2️⃣ 데이터 불러오기 (또는 예시 데이터)
# ---------------------------
try:
    data = pd.read_csv("data.csv")
except FileNotFoundError:
    st.warning("⚠️ data.csv 파일이 없어 예시 데이터를 사용합니다.")
    data = pd.DataFrame({
        "lat": [37.5665, 37.5651, 37.5643],
        "lon": [126.9780, 126.9821, 126.9750],
        "사고건수": [3, 5, 2],
        "발생일시": ["2025-01-01 08:00", "2025-01-01 22:00", "2025-01-02 15:00"]
    })

# 🔹 기존 데이터 처리 코드 추가 위치
# 예: 시간대별 필터, 구 선택, 사고유형 분석 등
# ----------------------------------------------------------
# 아래 예시는 기존 코드 일부 예시 구조 (예린씨 코드에 맞게 수정)
if "발생일시" in data.columns:
    data["발생일시"] = pd.to_datetime(data["발생일시"])
    selected_hour = st.slider("시간대 선택", 0, 23, 12)
    data = data[data["발생일시"].dt.hour == selected_hour]
# ----------------------------------------------------------

# ---------------------------
# 3️⃣ 지도 스타일 및 위치 설정
# ---------------------------
MAPBOX_STYLE = "mapbox://styles/mapbox/light-v11"  # 연한 회색 도로지도

view_state = pdk.ViewState(
    latitude=data["lat"].mean(),
    longitude=data["lon"].mean(),
    zoom=13,
    pitch=0
)

# ---------------------------
# 4️⃣ 시각화 레이어
# ---------------------------
layer = pdk.Layer(
    "ScatterplotLayer",
    data=data,
    get_position='[lon, lat]',
    get_color='[255, 0, 0, 160]',  # 반투명 빨간색 점
    get_radius=60,
    pickable=True
)

# ---------------------------
# 5️⃣ 지도 만들기 (이동/확대 제한)
# ---------------------------
deck = pdk.Deck(
    map_style=MAPBOX_STYLE,
    mapbox_key=MAPBOX_API_KEY,
    initial_view_state=view_state,
    layers=[layer],
    tooltip={"text": "사고건수: {사고건수}건"},
    interactive=False  # 확대/이동 불가능하게
)

# ---------------------------
# 6️⃣ Streamlit에 표시
# ---------------------------
st.title("🚗 교통사고 위치 시각화 지도")
st.pydeck_chart(deck)
