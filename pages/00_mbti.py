import streamlit as st
from PIL import Image

# ------------------ 기본 설정 ------------------
st.set_page_config(
    page_title="MBTI Drama & Movie Recommender",
    page_icon="🎬",
    layout="centered"
)

# ------------------ 스타일 ------------------
st.markdown("""
    <style>
        body {
            background: linear-gradient(135deg, #1f1c2c, #928dab);
            color: #fff;
        }
        .stApp {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        }
        h1, h2, h3 {
            text-align: center;
            color: #f5f5f5;
            font-family: 'Segoe UI', sans-serif;
        }
        .movie-card {
            background: rgba(255,255,255,0.08);
            border-radius: 20px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 0 20px rgba(255,255,255,0.1);
        }
        .movie-title {
            font-size: 1.3em;
            color: #fff;
            font-weight: 600;
        }
        .desc {
            font-size: 0.9em;
            color: #ddd;
        }
    </style>
""", unsafe_allow_html=True)

# ------------------ 데이터 ------------------
recommendations = {
    "INTJ": [
        {"title": "Sherlock (BBC)", "desc": "논리와 전략의 천재, 추리를 사랑하는 INTJ에게 완벽한 시리즈."},
        {"title": "Inception", "desc": "복잡한 구조와 사고의 깊이가 돋보이는 영화."}
    ],
    "INFP": [
        {"title": "Before Sunrise", "desc": "감정과 철학이 교차하는 낭만적인 여행."},
        {"title": "The Little Prince", "desc": "순수함과 상상력을 잃지 않는 INFP에게 어울림."}
    ],
    "ENTP": [
        {"title": "Suits", "desc": "지적이고 재치 넘치는 논쟁, ENTP의 천국."},
        {"title": "The Social Network", "desc": "혁신과 논리로 세상을 뒤흔드는 이야기."}
    ],
    "ESFP": [
        {"title": "La La Land", "desc": "감각적이고 순간을 즐기는 ESFP의 에너지."},
        {"title": "Emily in Paris", "desc": "자유롭고 화려한 도시 속의 자기표현."}
    ],
    "ISTJ": [
        {"title": "The King's Speech", "desc": "책임감과 헌신의 가치를 보여주는 영화."},
        {"title": "Interstellar", "desc": "논리와 인내로 우주를 탐험하는 이야기."}
    ],
    "ENFJ": [
        {"title": "Dead Poets Society", "desc": "영감을 주는 리더, ENFJ의 본질을 담은 명작."},
        {"title": "The Good Place", "desc": "윤리와 인간성에 대한 철학적 탐구."}
    ]
}

# ------------------ 본문 ------------------
st.markdown("<h1>🎬 MBTI 맞춤 드라마 & 영화 추천</h1>", unsafe_allow_html=True)
st.write("")
st.markdown("<h3>자신의 MBTI를 선택하세요</h3>", unsafe_allow_html=True)

# 선택 박스
mbti = st.selectbox(
    "MBTI 선택",
    sorted(list(recommendations.keys())),
    index=None,
    placeholder="예: INFP, ENTP ..."
)

# ------------------ 추천 결과 ------------------
if mbti:
    st.markdown(f"<h2>✨ {mbti}에게 어울리는 추천작 ✨</h2>", unsafe_allow_html=True)
    for rec in recommendations[mbti]:
        with st.container():
            st.markdown(f"""
                <div class='movie-card'>
                    <div class='movie-title'>{rec['title']}</div>
                    <div class='desc'>{rec['desc']}</div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.markdown("<p style='text-align:center; color:#bbb;'>MBTI를 선택하면 추천이 표시됩니다.</p>", unsafe_allow_html=True)

# ------------------ 하단 문구 ------------------
st.markdown("""
<hr style="border: 1px solid rgba(255,255,255,0.1);">
<p style='text-align:center; color:#888;'>
Created with ❤️ by Yerin
</p>
""", unsafe_allow_html=True)
