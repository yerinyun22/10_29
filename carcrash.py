# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

st.set_page_config(page_title="사고다발지역 안전지도(근사)", layout="wide")
url = "https://drive.google.com/file/d/1c3ULCZImSX4ns8F9cIE2wVsy8Avup8bu/view?usp=sharing"
df = pd.read_csv(url, encoding="cp949")  # 또는 cp949

# -------------------------
# 유틸: 거리(위도/경도) 계산 — Haversine (km)
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# -------------------------
# 데이터 로드
# -------------------------
@st.cache_data
def load_data(path="한국도로교통공단_교통사고다발지역_20250924.csv"):
    # try both utf-8 and cp949
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except Exception:
        df = pd.read_csv(path, encoding="cp949")
    # 표준화 컬럼명(있으면)
    df.columns = [c.strip() for c in df.columns]
    return df

data = load_data()

st.title("🛡️ 사고다발지역 안전지도 — 근사 안전경로 & 위험 레이어")
st.markdown(
    "이 앱은 한국도로교통공단의 사고다발지역 CSV를 사용해 **사고 위치 표출**, **히트맵/클러스터**, "
    "**필터/검색**, 그리고 **근사 안전경로(데이터 기반)** 를 제공합니다.\n\n"
    ":warning: 실제 내비게이션(도로 네트워크 기반 경로)은 외부 라우팅 API가 필요합니다. "
    "여기서는 데이터만으로 가능한 근사(위험 회피) 방식을 사용합니다."
)

# -------------------------
# 기본 컬럼 존재 여부 체크 (유저 요구에 맞춰 UI 활성화)
# -------------------------
has_latlon = {"위도", "경도"}.issubset(set(data.columns))
has_year = "사고연도" in data.columns or "연도" in data.columns
# 표준화: 사용 가능한 연도 컬럼명
year_col = "사고연도" if "사고연도" in data.columns else ("연도" if "연도" in data.columns else None)
type_col = "사고유형구분" if "사고유형구분" in data.columns else None
severity_related_cols = set(["사망자수", "중상자수", "경상자수", "사고건수", "사상자수"]) & set(data.columns)

# -------------------------
# 사이드바: 필터 & 검색
# -------------------------
st.sidebar.header("🔎 필터 · 검색 · 안전경로")

# 연도 필터 (있으면)
if year_col:
    years = sorted(data[year_col].dropna().unique().astype(int))
    sel_year = st.sidebar.slider("연도 선택", min_value=int(min(years)), max_value=int(max(years)), value=int(max(years)))
else:
    sel_year = None

# 사고유형 필터 (있으면)
if type_col:
    types = sorted(data[type_col].dropna().unique())
    sel_types = st.sidebar.multiselect("사고유형 필터", options=types, default=types)
else:
    sel_types = None

# 사고원인(컬럼 없으면 비활성)
possible_cause_cols = [c for c in data.columns if "원인" in c or "사고원인" in c or "발생원인" in c]
cause_col = possible_cause_cols[0] if possible_cause_cols else None
if cause_col:
    causes = sorted(data[cause_col].dropna().unique())
    sel_causes = st.sidebar.multiselect("사고원인 필터", options=causes, default=causes)
else:
    sel_causes = None

# 날짜 필터(데이터기준일자 등)
date_col = None
for c in data.columns:
    if "일자" in c or "date" in c.lower() or "날짜" in c:
        date_col = c
        break

if date_col:
    # try parse dates
    try:
        data[date_col + "_parsed"] = pd.to_datetime(data[date_col], errors="coerce")
        min_d = data[date_col + "_parsed"].min()
        max_d = data[date_col + "_parsed"].max()
        sel_dates = st.sidebar.date_input("기간 필터", value=(max_d.date(), max_d.date()), min_value=min_d.date(), max_value=max_d.date())
        # sel_dates is tuple(start,end)
    except Exception:
        date_col = None

# 검색(지역명/위치명)
search_text = st.sidebar.text_input("검색(지역명 / 위치코드 / 위치명) — 빈칸=전체", "")

# 안전경로 입력 (출발/도착 선택) — 데이터에 있는 위치명 목록 사용
loc_name_col = None
for c in ["사고지역위치명", "사고다발지역시도시군구", "위치코드"]:
    if c in data.columns:
        loc_name_col = c
        break

loc_options = data[loc_name_col].astype(str).unique().tolist() if loc_name_col else []

st.sidebar.markdown("---")
st.sidebar.subheader("🚗 근사 안전경로(데이터 기반)")
start_sel = st.sidebar.selectbox("출발지 (데이터 위치 중 선택)", options=loc_options, index=0 if loc_options else -1)
end_sel = st.sidebar.selectbox("도착지 (데이터 위치 중 선택)", options=loc_options, index=len(loc_options)-1 if loc_options else -1)
# 후보 수, 샘플 포인트 수
candidate_count = st.sidebar.slider("경로 후보 수", 3, 9, 5)
samples_per_candidate = st.sidebar.slider("경로 샘플 점 개수(정밀도)", 10, 80, 30)
avoid_radius_km = st.sidebar.slider("위험 가중 반경 (km)", 0.2, 3.0, 0.7)

# 위험 구간 경고: 현재 위치(위도/경도) 수동 입력(또는 선택)
st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ 위험 구간 경고 (임의 위치)")
alert_lat = st.sidebar.number_input("위도 입력", value=float(data["위도"].mean()) if has_latlon else 37.56)
alert_lon = st.sidebar.number_input("경도 입력", value=float(data["경도"].mean()) if has_latlon else 126.97)
alert_radius_km = st.sidebar.slider("경고 반경 (km)", 0.1, 5.0, 0.5)
# -------------------------
# 데이터 필터링 적용
# -------------------------
df = data.copy()

if sel_year and year_col:
    df = df[df[year_col] == sel_year]

if sel_types and type_col:
    df = df[df[type_col].isin(sel_types)]

if sel_causes and cause_col:
    df = df[df[cause_col].isin(sel_causes)]

if date_col:
    start_d, end_d = sel_dates
    mask = (df[date_col + "_parsed"].dt.date >= start_d) & (df[date_col + "_parsed"].dt.date <= end_d)
    df = df[mask]

if search_text:
    search_text = search_text.strip()
    # search in possible text columns
    text_cols = [c for c in df.columns if df[c].dtype == object]
    mask = pd.Series(False, index=df.index)
    for c in text_cols:
        mask = mask | df[c].astype(str).str.contains(search_text, case=False, na=False)
    df = df[mask]

# -------------------------
# 색상/심각도 계산(간단 가중치)
# -------------------------
# 우선 '사망자수' 있는지 확인하고, 없으면 '사상자수'나 '중상자수'로 대체
def severity_score(row):
    score = 0.0
    if "사망자수" in row.index:
        score += 10.0 * (row.get("사망자수", 0) or 0)
    if "중상자수" in row.index:
        score += 3.0 * (row.get("중상자수", 0) or 0)
    if "경상자수" in row.index:
        score += 1.0 * (row.get("경상자수", 0) or 0)
    # 사고건수도 가미
    if "사고건수" in row.index:
        score += 0.5 * (row.get("사고건수", 0) or 0)
    return score

if len(df) > 0:
    df["sev_score"] = df.apply(severity_score, axis=1)
else:
    df["sev_score"] = []

# 색상 매핑 함수
def severity_to_color(s):
    # s >= 10 : 아주 위험(진한 빨강), 5~10: 빨강, 2~5: 주황, <2: 노랑/연한회색
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

if len(df) > 0:
    df["color"] = df["sev_score"].apply(severity_to_color)
else:
    df["color"] = []

# -------------------------
# 메인 레이아웃: 지도 + 컨트롤
# -------------------------
st.subheader("지도 · 히트맵 · 클러스터 · 마커")
if not has_latlon:
    st.error("데이터에 '위도' / '경도' 컬럼이 필요합니다. 현재 파일에 해당 컬럼이 없습니다.")
else:
    # view 초기값: 대한민국(또는 데이터 중심)
    center_lat = float(df["위도"].mean()) if not np.isnan(df["위도"].mean()) else 37.56
    center_lon = float(df["경도"].mean()) if not np.isnan(df["경도"].mean()) else 126.97

    # 피처: Scatter(마커), Heatmap, Hexagon(클러스터), Line(안전경로)
    layers = []

    # 히트맵 레이어
    heat_layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["경도", "위도"],
        aggregation="SUM",
        weight="sev_score" if "sev_score" in df.columns else None,
        radiusPixels=60,
    )
    layers.append(heat_layer)

    # Hexagon 클러스터 레이어 (집중도 표시)
    hex_layer = pdk.Layer(
        "HexagonLayer",
        data=df,
        get_position=["경도", "위도"],
        radius=200,  # meters (approx)
        elevation_scale=50,
        elevation_range=[0, 3000],
        pickable=True,
        extruded=True,
    )
    layers.append(hex_layer)

    # 사고 마커(심각도 색상)
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["경도", "위도"],
        get_color="color",
        get_radius=60,
        pickable=True,
    )
    layers.append(scatter)

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=6, pitch=0)

    tooltip = {
        "html": "<b>{사고지역위치명}</b><br/>사고건수: {사고건수} / 사상자: {사상자수} / 심각도:{sev_score}",
        "style": {"color": "white"}
    }

    deck = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=layers,
        tooltip=tooltip
    )

    st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# 구별/유형별 통계 (plotly)
# -------------------------
st.subheader("통계 · 필터된 결과 요약")
if "사고다발지역시도시군구" in df.columns and "사고건수" in df.columns:
    by_dist = df.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수", title="구별 사고건수 Top 15")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("구별 사고건수 그래프를 만들기 위해 '사고다발지역시도시군구'와 '사고건수' 컬럼이 필요합니다.")

if type_col and "사고건수" in df.columns:
    by_type = df.groupby(type_col)["사고건수"].sum().sort_values(ascending=False).reset_index()
    fig2 = px.pie(by_type, values="사고건수", names=type_col, title="사고유형별 비율")
    st.plotly_chart(fig2, use_container_width=True)

# -------------------------
# 위험 구간 경고 (단순 근접 기반)
# -------------------------
st.subheader("위험 구간 경고 (입력 좌표 기준)")
if has_latlon:
    # 거리 계산: alert point 와 각 사고지점 간 거리 계산
    df["dist_to_alert_km"] = df.apply(lambda r: haversine(alert_lat, alert_lon, float(r["위도"]), float(r["경도"])), axis=1)
    nearby = df[df["dist_to_alert_km"] <= alert_radius_km]
    st.write(f"선택 반경 {alert_radius_km} km 내 사고다발지 수: {len(nearby)}")
    if len(nearby) > 0:
        # 요약
        st.dataframe(nearby[["사고지역위치명", "사고건수", "사상자수", "dist_to_alert_km"]].sort_values("dist_to_alert_km").head(10))
    else:
        st.info("선택한 반경 내 위험지점이 없습니다.")
else:
    st.info("위치 데이터(위도/경도)가 없어 위험구간 경고를 계산할 수 없습니다.")

# -------------------------
# 근사 안전경로 생성 및 시각화
# -------------------------
st.subheader("근사 안전경로 (데이터 기반 후보 생성 및 위험도 비교)")

def get_coords_for_loc(name):
    # loc_name_col을 기준으로 해당 위치의 평균 좌표 반환
    subset = data[data[loc_name_col].astype(str) == str(name)]
    if len(subset) == 0:
        return None
    return float(subset["위도"].mean()), float(subset["경도"].mean())

start_coord = get_coords_for_loc(start_sel) if loc_name_col and start_sel else None
end_coord = get_coords_for_loc(end_sel) if loc_name_col and end_sel else None

if (start_coord is None) or (end_coord is None):
    st.info("출발지/도착지의 좌표를 찾을 수 없습니다 (데이터 위치 선택이 필요).")
else:
    st.write("출발:", start_sel, "위치:", start_coord)
    st.write("도착:", end_sel, "위치:", end_coord)

    # 후보 경로 생성: 원래 직선 경로 + 여러 각도 offset으로 조금씩 우회하는 후보들
    def sample_line(lat1, lon1, lat2, lon2, n):
        lats = np.linspace(lat1, lat2, n)
        lons = np.linspace(lon1, lon2, n)
        return list(zip(lats, lons))

    def offset_candidate(lat1, lon1, lat2, lon2, offset_deg):
        # offset_deg : degree to rotate around midpoint in lat/lon space (approx)
        mid_lat = (lat1 + lat2) / 2
        mid_lon = (lon1 + lon2) / 2
        # vector from mid to endpoints
        v1 = np.array([lat1 - mid_lat, lon1 - mid_lon])
        v2 = np.array([lat2 - mid_lat, lon2 - mid_lon])
        # rotate both vectors by offset_deg
        theta = np.radians(offset_deg)
        R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
        nv1 = R.dot(v1)
        nv2 = R.dot(v2)
        # reconstruct endpoints and sample between them
        nlat1, nlon1 = mid_lat + nv1[0], mid_lon + nv1[1]
        nlat2, nlon2 = mid_lat + nv2[0], mid_lon + nv2[1]
        return sample_line(nlat1, nlon1, nlat2, nlon2, samples_per_candidate)

    # 평가 함수: 경로의 위험 점수 = 각 샘플 포인트에서 주변 사고의 거리 기반 위험 합
    def path_risk_score(path_points, accidents_df, radius_km=avoid_radius_km):
        total = 0.0
        # for each sample point, sum gaussian-like weight from accidents
        for (plat, plon) in path_points:
            # compute distances vectorized
            dists = haversine_vectorized(plat, plon, accidents_df["위도"].values, accidents_df["경도"].values)
            # only consider within radius; weight = sev_score * exp(-(d/r)^2)
            within_mask = dists <= (radius_km * 3)  # consider up to 3*r
            if not np.any(within_mask):
                continue
            rel = dists[within_mask] / (radius_km + 1e-6)
            weights = np.exp(- (rel**2))
            sev = accidents_df["sev_score"].values[within_mask]
            total += np.sum(weights * (sev + 0.1))  # avoid zero
        return total

    # vectorized haversine over numpy arrays
    def haversine_vectorized(lat1, lon1, lat_arr, lon_arr):
        R = 6371.0
        lat1r = np.radians(lat1)
        lon1r = np.radians(lon1)
        lat2r = np.radians(lat_arr)
        lon2r = np.radians(lon_arr)
        dlat = lat2r - lat1r
        dlon = lon2r - lon1r
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    # generate candidate offsets: symmetric offsets between -max to +max degrees
    max_offset = 30  # degrees rotation max
    offsets = np.linspace(-max_offset, max_offset, candidate_count)
    candidates = []
    for off in offsets:
        pts = offset_candidate(start_coord[0], start_coord[1], end_coord[0], end_coord[1], off)
        candidates.append(pts)

    # compute risk for each candidate using current filtered df (we consider all accidents in df)
    candidate_scores = []
    for pts in candidates:
        score = path_risk_score(pts, df, radius_km=avoid_radius_km)
        candidate_scores.append(score)

    # choose best (min risk)
    best_idx = int(np.argmin(candidate_scores))
    best_path = candidates[best_idx]

    st.write(f"생성된 후보 {len(candidates)}개 중 위험도 최저 경로: 후보 #{best_idx+1} (score={candidate_scores[best_idx]:.2f})")

    # 시각화: 위 지도 위에 최저경로 선으로 표시
    if has_latlon:
        line_layer = pdk.Layer(
            "LineLayer",
            data=[{"path": [(p[1], p[0]) for p in best_path], "name": "best"}],
            get_path="path",
            get_width=6,
            get_color=[30, 144, 255],
        )

        deck_with_path = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=7),
            layers=[heat_layer, hex_layer, scatter, line_layer],
            tooltip=tooltip
        )
        st.pydeck_chart(deck_with_path, use_container_width=True)

    # 표로 후보 비교
    comp_df = pd.DataFrame({"candidate": list(range(1, len(candidate_scores) + 1)), "offset_deg": offsets, "risk_score": candidate_scores})
    st.table(comp_df.sort_values("risk_score").reset_index(drop=True))

# -------------------------
# 마무리: 참고 및 한계
# -------------------------
st.markdown("---")
st.subheader("참고 및 한계")
st.markdown(
    """
- 안전경로는 **도로 네트워크가 아닌, 사고 데이터 분포 기반의 근사(우회 후보 생성)** 입니다.
  실제 도로 기반 경로 최적화(실시간 교통, 도로 차로 등)는 **외부 라우팅 API**(OSRM, Google Directions 등) + 교통 데이터가 필요합니다.
- 사고원인/정확 발생시각 등 데이터 컬럼이 파일에 없을 경우 관련 필터는 비활성화됩니다.
- 실사용 수준의 '실시간 위험 알림' 기능을 만들려면 모바일 위치 접근 및 백엔드(서버) 형태의 지속적 모니터링이 필요합니다.
"""
)

