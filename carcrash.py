# 메뉴 구성
menu = st.sidebar.radio("메뉴 선택", ["지도 보기", "통계 보기", "시민 참여"])

# =====================================================
# 지도 보기
# =====================================================
if menu == "지도 보기":
    st.title("🗺️ 대한민국 사고다발지역 지도")

    has_latlon = {"위도", "경도"}.issubset(data.columns)
    if not has_latlon:
        st.error("⚠️ 위도와 경도 컬럼이 필요합니다.")
    else:
        # 심각도 계산
        def severity_score(row):
            score = 0
            if "사망자수" in row: score += 10 * (row["사망자수"] or 0)
            if "중상자수" in row: score += 3 * (row["중상자수"] or 0)
            if "경상자수" in row: score += 1 * (row["경상자수"] or 0)
            if "사고건수" in row: score += 0.5 * (row["사고건수"] or 0)
            return score

        df = data.copy()
        df["sev_score"] = df.apply(severity_score, axis=1)

        # 색상
        def severity_to_color(s):
            if s >= 10: return [255, 0, 0, 230]
            elif s >= 5: return [255, 80, 80, 200]
            elif s >= 2: return [255, 150, 150, 170]
            else: return [255, 200, 200, 140]
        df["color"] = df["sev_score"].apply(severity_to_color)

        center_lat = float(df["위도"].mean())
        center_lon = float(df["경도"].mean())

        layers = [
            pdk.Layer(
                "HeatmapLayer",
                data=df,
                get_position=["경도","위도"],
                aggregation="SUM",
                weight="sev_score",
                radiusPixels=60
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position=["경도","위도"],
                get_color="color",
                get_radius=70,
                pickable=True
            )
        ]

        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=6)
        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=view_state,
            layers=layers,
            tooltip={
                "html": "<b>{사고지역위치명}</b><br/>사고건수: {사고건수}<br/>사상자수: {사상자수}",
                "style": {"color": "white"}
            }
        )
        st.pydeck_chart(deck, use_container_width=True)

# =====================================================
# 통계 보기
# =====================================================
elif menu == "통계 보기":
    st.title("📊 사고 통계 분석")

    # 통계 유형 선택
    stats_type = st.radio("보고 싶은 통계 유형 선택", ["지역별 사고 건수", "사고유형별 비율"])

    df_stats = data.copy()

    if stats_type == "지역별 사고 건수" and "사고다발지역시도시군구" in df_stats.columns:
        by_dist = df_stats.groupby("사고다발지역시도시군구")["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(by_dist.head(15), x="사고다발지역시도시군구", y="사고건수", title="구별 사고건수 Top 15", text="사고건수")
        st.plotly_chart(fig, use_container_width=True)

    elif stats_type == "사고유형별 비율" and "사고유형구분" in df_stats.columns:
        by_type = df_stats.groupby("사고유형구분")["사고건수"].sum().sort_values(ascending=False).reset_index()
        fig2 = px.pie(by_type, values="사고건수", names="사고유형구분", title="사고유형별 비율")
        st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# 시민 참여
# =====================================================
elif menu == "시민 참여":
    st.title("🙋 시민 참여 공간")
    tab1, tab2, tab3 = st.tabs(["🚨 위험 구역 제보", "🧱 개선 요청 게시판", "🚸 교통안전 캠페인 참여"])

    # 위험 구역 제보
    with tab1:
        st.subheader("🚨 위험 구역 제보하기")
        region = st.text_input("📍 위치 또는 지역명")
        issue_type = st.selectbox("🚧 문제 유형", ["신호등 고장", "가로등 부족", "횡단보도 없음", "도로 파손", "기타"])
        detail = st.text_area("📝 상세 설명")
        if st.button("제보 제출"):
            st.success("✅ 제보가 접수되었습니다. 검토 후 지도에 반영됩니다.")

    # 개선 요청 게시판
    with tab2:
        st.subheader("🧱 지역 개선 요청 게시판")
        title = st.text_input("제목")
        content = st.text_area("내용")
        if st.button("요청 등록"):
            st.success("✅ 요청이 등록되었습니다. 담당 기관에 전달됩니다.")

    # 교통안전 캠페인 참여
    with tab3:
        st.subheader("🚸 교통안전 캠페인 참여")
        choice = st.radio("캠페인 선택", ["보행자 우선 캠페인", "음주운전 근절 서약", "안전벨트 착용 인증"])
        if st.button("참여하기"):
            st.success(f"🎉 '{choice}' 캠페인에 참여해주셔서 감사합니다!")
