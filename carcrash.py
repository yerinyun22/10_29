import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import os

# -------------------------
# Mapbox API 키
# -------------------------
os.environ["MAPBOX_API_KEY"] = "YOUR_MAPBOX_TOKEN"  # ← 본인 토큰 넣기

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(page_title="사고다발지역 안전지도", layout="wide", page_icon="🛡️")

# -------------------------
# CSS: 배경 흰색, 글씨 검은색
# -------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: white;
        color: black;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Haversine 거리 계산
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# -------------------------
# 데이터 로드
# -------------------------
@st.cache_data
def load_data(url):
    file_id = url.split('/')[-2]
    csv_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        df = pd.read_csv(csv_url, encoding="utf-8")
    except Exception:
        df = pd.read_csv(csv_url, encoding="cp949")
    df.columns = [c.strip() for c in df.columns]
    return df

data = load_data("https://drive.google.com/file/d/1c3ULCZImSX4ns8F9cIE2wVsy8Avup8bu/view?usp=sharing")

# -------------------------
# 사이드바 필터
# -------------------------
st.sidebar.header("🔎 필터 · 검색 · 안전경로")

year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
if year_col:
    min_year, max_year = int(data[year_col].min()), int(data[year_col].max())
    sel_year_range = st.sidebar.slider("연도 범위 선택", min_value=min_year, max_value=max_year, value=(min_year, max_year))
else:
    sel_year_range = None

type_col = "사고유형구분" if "사고유형구분" in data.columns else None
sel_types = st.sidebar.multiselect(
    "사고유형 필터",
    options=sorted(data[type_col].dropna().unique()) if type_col else [],
    default=None
)

possible_cause_cols = [c for c in data.columns if "원인" in c]
cause_col = possible_cause_cols[0] if possible_cause_cols else None
sel_causes = st.sidebar.multiselect(
    "사고원인 필터",
    options=sorted(data[cause_col].dropna().unique()) if cause_col else [],
    default=None
)

# -------------------------
# 데이터 필터링
# -------------------------
df = data.copy()
if sel_year_range and year_col:
    df = df[(df[year_col] >= sel_year_range[0]) & (df[year_col] <= sel_year_range[1])]
if sel_types and type_col:
    df = df[df[type_col].isin(sel_types)]
if sel_causes and cause_col:
    df = df[df[cause_col].isin(sel_causes)]

# -------------------------
# 심각도 계산
# -------------------------
def severity_score(row):
    score = 0.0
    score += 10.0 * (row.get("사망자수", 0) or 0)
    score += 3.0 * (row.get("중상자수", 0) or 0)
    score += 1.0 * (row.get("경상자수", 0) or 0)
    score += 0.5 * (row.get("사고건수", 0) or 0)
    return score

df["sev_score"] = df.apply(severity_score, axis=1) if len(df) > 0 else []
def severity_to_color(s):
    if s >= 10:
        return [180, 0, 0, 200]
    elif s >= 5:
        return [230, 40, 40, 180]
    elif s >= 2:
        return [255, 140, 0, 150]
    elif s > 0:
        return [255, 210, 0, 130]
    else:
        return [150, 150, 150, 90]

df["color"] = df["sev_score"].apply(severity_to_color) if len(df) > 0 else []

# -------------------------
# 지도 시각화
# -------------------------
st.title("🛡️ 사고다발지역 안전지도 — 커스텀 배경")

if not {"위도", "경도"}.issubset(df.columns):
    st.error("위도/경도 컬럼이 필요합니다.")
else:
    center_lat = float(df["위도"].mean())
    center_lon = float(df["경도"].mean())

    # BitmapLayer: 배경 이미지
    image_layer = pdk.Layer(
        "BitmapLayer",
        data=[{
            "coordinates": [[124.5, 33.0], [131.0, 33.0], [131.0, 39.5], [124.5, 39.5]],
            "image": "/mnt/data/cdd532db-9d32-4d58-a4d8-0729cdda79c7.png"
        }],
        bounds=[[124.5, 33.0], [131.0, 39.5]],
        opacity=1.0
    )

    layers = [
        image_layer,
        pdk.Layer(
            "HeatmapLayer",
            data=df,
            get_position=["경도", "위도"],
            aggregation="SUM",
            weight="sev_score",
            radiusPixels=60
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["경도", "위도"],
            get_color="color",
            get_radius=60,
            pickable=True
        )
    ]

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=7,
        pitch=0
    )

    # Deck: Mapbox URL 사용 → BitmapLayer와 충돌 방지
    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v10",  # 안정적 URL 사용
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": "<b>{사고지역위치명}</b><br/>사고건수: {사고건수}<br/>사상자: {사상자수}" if "사고지역위치명" in df.columns else "",
            "style": {"color": "black"}
        },
        controller=False
    )

    st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# 통계
# -------------------------
st.subheader("📊 통계 요약")

if "사고다발지역시도시군구" in df.columns and "사고건수" in df.columns:
    by_dist = df.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수", title="구별 사고건수 Top 15")
    st.plotly_chart(fig, use_container_width=True)

if type_col and "사고건수" in df.columns:
    by_type = df.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig2 = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율")
    st.plotly_chart(fig2, use_container_width=True)
