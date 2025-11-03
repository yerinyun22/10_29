import streamlit as st
import pandas as pd
import pydeck as pdk
from math import radians, sin, cos, sqrt, atan2

st.set_page_config(page_title="🛡️ 대한민국 안전지도 (MapLibre)", layout="wide")

# -------------------------
# 데이터 로드
# -------------------------
@st.cache_data
def load_data(path="data.csv"):
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        st.warning("⚠️ data.csv 파일이 없어 예시 데이터를 사용합니다.")
        df = pd.DataFrame({
            "위도": [37.5665, 37.5651, 37.5643],
            "경도": [126.9780, 126.9821, 126.9750],
            "사망자수": [0, 1, 0],
            "중상자수": [1, 2, 1],
            "경상자수": [2, 1, 1],
            "사고건수": [3, 5, 2],
            "사고지역위치명": ["시청근처","광화문","종로3가"]
        })
    df.columns = [c.strip() for c in df.columns]
    return df

data = load_data()

# -------------------------
# 심각도 점수 계산 (예전 로직 통합)
# -------------------------
def severity_score(row):
    score = 0
    # 안전하게 키 존재 확인
    if "사망자수" in row and pd.notna(row["사망자수"]):
        score += 10 * int(row["사망자수"] or 0)
    if "중상자수" in row and pd.notna(row["중상자수"]):
        score += 3 * int(row["중상자수"] or 0)
    if "경상자수" in row and pd.notna(row["경상자수"]):
        score += 1 * int(row["경상자수"] or 0)
    if "사고건수" in row and pd.notna(row["사고건수"]):
        # 사고건수가 소수일 가능성 대비 안전 처리
        try:
            score += 0.5 * float(row["사고건수"] or 0)
        except:
            pass
    return score

data["sev_score"] = data.apply(severity_score, axis=1)

def severity_to_color(s):
    if s >= 10: return [255, 0, 0, 230]
    elif s >= 5: return [255, 80, 80, 200]
    elif s >= 2: return [255, 150, 150, 170]
    else: return [255, 200, 200, 140]

data["color"] = data["sev_score"].apply(severity_to_color)

# -------------------------
# 사이드바: 필터 예시 (연도/유형 등 기존 로직 여기에 추가)
# -------------------------
st.sidebar.title("필터")
# (데이터에 연도/유형 컬럼이 있으면 여기에서 필터 UI 추가)

# -------------------------
# 지도 준비 (MapLibre + OSM 사용)
# -------------------------
if not {"위도","경도"}.issubset(data.columns):
    st.error("위도와 경도 컬럼이 필요합니다. 컬럼명이 '위도' '경도'인지 확인하세요.")
else:
    center_lat = float(data["위도"].mean())
    center_lon = float(data["경도"].mean())

    # 뷰 상태
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11, pitch=0)

    layers = [
        pdk.Layer(
            "HeatmapLayer",
            data=data,
            get_position=["경도","위도"],
            aggregation="SUM",
            weight="sev_score",
            radiusPixels=60
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=data,
            get_position=["경도","위도"],
            get_color="color",
            get_radius=70,
            pickable=True
        )
    ]

    deck = pdk.Deck(
        map_provider=None,    # mapbox 비활성화
        map_style=None,
        initial_view_state=view_state,
        layers=layers,
        tooltip={"html":"<b>{사고지역위치명}</b><br/>사고건수: {사고건수}<br/>사상자수: {사망자수}",
                 "style":{"color":"white"}},
        # interactive=True 로 놔도 되지만, 필요하면 False로 고정 가능
    )

    # deck.to_html에 MapLibre (maplibre-gl) 스크립트를 추가.
    # 아래 스크립트 중 window.mapboxgl = window.maplibregl; 가 핵심 — deck.gl이 mapboxgl을 참조하므로 maplibregl을 대신 지정.
    extra_head = """
    <script src="https://unpkg.com/maplibre-gl@2.4.0/dist/maplibre-gl.js"></script>
    <link href="https://unpkg.com/maplibre-gl@2.4.0/dist/maplibre-gl.css" rel="stylesheet"/>
    <script>
      // deck.gl 내부가 mapboxgl을 참조하므로 maplibre를 mapboxgl 변수로 할당
      window.mapboxgl = window.maplibregl;
    </script>
    <style>
      .mapboxgl-ctrl-attrib { font-size: 11px; }
    </style>
    """

    html = deck.to_html(as_string=True, mapbox_key=None, extra_html_head=extra_head)
    st.components.v1.html(html, height=720)

    # OSM 저작권/출처 표기 (필수 아님, 권장)
    st.markdown("<small>데이터: OpenStreetMap contributors — 지도 타일: OSM</small>", unsafe_allow_html=True)

# -------------------------
# 통계 보기(간단)
# -------------------------
st.sidebar.markdown("---")
st.sidebar.write("데이터 건수:", len(data))
