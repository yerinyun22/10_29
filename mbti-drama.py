import streamlit as st
from textwrap import dedent

st.set_page_config(page_title="MBTI Korean Picks", page_icon="🎥", layout="wide")

# --- style ---
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(120deg,#0f0c29 0%,#302b63 50%,#24243e 100%); }
    .title { text-align:center; font-size:44px; margin-bottom:0.2rem; color:#fff; font-weight:700; }
    .subtitle { text-align:center; color:rgba(255,255,255,0.85); margin-top:0; margin-bottom:1.5rem }
    .card { background: rgba(255,255,255,0.04); padding:18px; border-radius:14px; box-shadow: 0 6px 18px rgba(2,6,23,0.6); }
    .movie-title { font-size:18px; font-weight:700; color:#fff }
    .movie-meta { font-size:12px; color:rgba(255,255,255,0.6); margin-bottom:8px }
    .movie-desc { color:rgba(255,255,255,0.9); font-size:14px }
    .mbti-btn { background: linear-gradient(90deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); color:#fff; border-radius:10px; padding:8px 12px; margin:6px; display:inline-block; cursor:pointer }
    .mbti-grid { text-align:center; margin-bottom:1rem }
    a.link { color:#9be7ff; text-decoration:none }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="title">MBTI 기반 한국 영화·드라마 추천</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">당신의 MBTI에 어울리는 한국 작품을 감각적으로 추천합니다.</div>', unsafe_allow_html=True)

# --- DATA: 16 MBTI mapping (Korean films & dramas) ---
RECS = {
    "ISTJ": [
        {"title": "A Taxi Driver (택시운전사)", "year": "2017", "type": "Film", "desc": "책임감 있는 평범한 사람의 용기와 역사적 순간을 다룬 실화 기반 영화.", "link": "https://search.naver.com/search.naver?query=택시운전사"},
        {"title": "1987: When the Day Comes (1987)", "year": "2017", "type": "Film", "desc": "시스템과 절차, 진실을 지키려는 사람들의 투쟁을 그린 작품.", "link": "https://search.naver.com/search.naver?query=1987"},
    ],
    "ISFJ": [
        {"title": "Hospital Playlist (슬기로운 의사생활)", "year": "2020", "type": "Drama", "desc": "사람을 돌보는 따뜻한 시선과 우정이 중심인 드라마.", "link": "https://search.naver.com/search.naver?query=슬기로운+의사생활"},
        {"title": "Sunny (써니)", "year": "2011", "type": "Film", "desc": "추억과 우정, 보살핌의 감성이 잘 드러나는 작품.", "link": "https://search.naver.com/search.naver?query=써니+영화"},
    ],
    "INFJ": [
        {"title": "The Handmaiden (아가씨)", "year": "2016", "type": "Film", "desc": "섬세한 심리와 윤리·정체성의 충돌을 예술적으로 그려낸 영화.", "link": "https://search.naver.com/search.naver?query=아가씨"},
        {"title": "Mr. Sunshine (미스터 션샤인)", "year": "2018", "type": "Drama", "desc": "역사적 배경 속에서 인간의 이상과 내면을 탐구하는 대작 드라마.", "link": "https://search.naver.com/search.naver?query=미스터+션샤인"},
    ],
    "INTJ": [
        {"title": "Oldboy (올드보이)", "year": "2003", "type": "Film", "desc": "복잡한 복수극과 치밀한 플롯 — 전략과 통찰을 즐기는 타입에게.", "link": "https://search.naver.com/search.naver?query=올드보이"},
        {"title": "Signal (시그널)", "year": "2016", "type": "Drama", "desc": "논리와 단서, 시간의 퍼즐을 풀어나가는 심리 수사 드라마.", "link": "https://search.naver.com/search.naver?query=시그널+드라마"},
    ],
    "ISTP": [
        {"title": "Memories of Murder (살인의 추억)", "year": "2003", "type": "Film", "desc": "현장 감각과 문제 해결 능력을 자극하는 사실 기반 범죄극.", "link": "https://search.naver.com/search.naver?query=살인의+추억"},
        {"title": "The Wailing (곡성)", "year": "2016", "type": "Film", "desc": "감각적이고 즉흥적인 상황 대처가 중요한 미스터리 호러.", "link": "https://search.naver.com/search.naver?query=곡성"},
    ],
    "ISFP": [
        {"title": "The Beauty Inside (뷰티 인사이드)", "year": "2015", "type": "Film", "desc": "감성적이고 미적 경험을 중시하는 사람에게 어울리는 로맨스.", "link": "https://search.naver.com/search.naver?query=뷰티+인사이드"},
        {"title": "A Moment to Remember (내 머리 속의 지우개)", "year": "2004", "type": "Film", "desc": "섬세한 감정선과 일상의 미세한 아름다움을 담은 작품.", "link": "https://search.naver.com/search.naver?query=내+머리+속의+지우개"},
    ],
    "INFP": [
        {"title": "A Werewolf Boy (늑대소년)", "year": "2012", "type": "Film", "desc": "순수하고 상상력 가득한 감수성이 잘 어울리는 판타지 로맨스.", "link": "https://search.naver.com/search.naver?query=늑대소년"},
        {"title": "Tune in for Love (지금 만나러 갑니다랑은 다른 작품 느낌)", "year": "2019", "type": "Film", "desc": "낭만적이고 감성적인 서사가 중심인 멜로 영화.", "link": "https://search.naver.com/search.naver?query=유열의+음악앨범"},
    ],
    "INTP": [
        {"title": "Stranger (비밀의 숲)", "year": "2017", "type": "Drama", "desc": "논리적 추론과 제도 분석을 즐기는 타입에게 적합한 법정 스릴러.", "link": "https://search.naver.com/search.naver?query=비밀의+숲"},
        {"title": "Burning (버닝)", "year": "2018", "type": "Film", "desc": "모호성과 해석 여지를 남기는 서사를 좋아하는 사람에게.", "link": "https://search.naver.com/search.naver?query=버닝+영화"},
    ],
    "ESTP": [
        {"title": "Train to Busan (부산행)", "year": "2016", "type": "Film", "desc": "강렬한 액션과 즉각적인 의사결정이 필요한 스릴러.", "link": "https://search.naver.com/search.naver?query=부산행"},
        {"title": "The Man from Nowhere (아저씨)", "year": "2010", "type": "Film", "desc": "실전 능력과 액션, 보호 본능을 자극하는 걸작.", "link": "https://search.naver.com/search.naver?query=아저씨+영화"},
    ],
    "ESFP": [
        {"title": "Crash Landing on You (사랑의 불시착)", "year": "2019", "type": "Drama", "desc": "화려하고 감정 표현이 풍부한 순간을 즐기는 타입에게.", "link": "https://search.naver.com/search.naver?query=사랑의+불시착"},
        {"title": "Weightlifting Fairy Kim Bok-joo (역도요정 김복주)", "year": "2016", "type": "Drama", "desc": "경쾌하고 에너지 넘치는 청춘 로맨스 드라마.", "link": "https://search.naver.com/search.naver?query=역도요정+김복주"},
    ],
    "ENFP": [
        {"title": "Reply 1988 (응답하라 1988)", "year": "2015", "type": "Drama", "desc": "따뜻한 인간관계와 호기심, 성장 이야기를 좋아하는 타입에게.", "link": "https://search.naver.com/search.naver?query=응답하라+1988"},
        {"title": "Itaewon Class (이태원 클라쓰)", "year": "2020", "type": "Drama", "desc": "자유로운 아이디어와 사람에 대한 공감이 강한 ENFP에게.", "link": "https://search.naver.com/search.naver?query=이태원+클라쓰"},
    ],
    "ENTP": [
        {"title": "Vincenzo (빈센조)", "year": "2021", "type": "Drama", "desc": "재치있고 반전 많은 전개를 즐기는 사람에게 잘 맞는 흑코미디적 요소의 드라마.", "link": "https://search.naver.com/search.naver?query=빈센조"},
        {"title": "The Producers (프로듀사)", "year": "2015", "type": "Drama", "desc": "업계 풍자와 빠른 대사 교환을 즐기는 타입에게 유쾌한 선택.", "link": "https://search.naver.com/search.naver?query=프로듀사+드라마"},
    ],
    "ESTJ": [
        {"title": "The Attorney (변호인)", "year": "2013", "type": "Film", "desc": "책임감 있는 리더십과 정의감이 핵심인 실화 기반 드라마.", "link": "https://search.naver.com/search.naver?query=변호인+영화"},
        {"title": "Hotel del Luna? (호텔 델루나) — 좀 다른 장르지만 연출이 강렬함", "year": "2019", "type": "Drama", "desc": "조직과 운영, 강한 의사결정을 보는 재미.", "link": "https://search.naver.com/search.naver?query=호텔+델루나"},
    ],
    "ESFJ": [
        {"title": "My Mister (나의 아저씨)", "year": "2018", "type": "Drama", "desc": "공감과 돌봄을 중심으로 한 인간 드라마 — 감정 기운을 잘 다루는 작품.", "link": "https://search.naver.com/search.naver?query=나의+아저씨"},
        {"title": "Reply 1997 (응답하라 1997)", "year": "2012", "type": "Drama", "desc": "친구와 가족 중심의 정서적 공감대를 잘 형성하는 드라마.", "link": "https://search.naver.com/search.naver?query=응답하라+1997"},
    ],
    "ENFJ": [
        {"title": "Itaewon Class (이태원 클라쓰)", "year": "2020", "type": "Drama", "desc": "비전과 사람을 이끄는 힘이 돋보이는 리더형에게 추천.", "link": "https://search.naver.com/search.naver?query=이태원+클라쓰"},
        {"title": "Reply 1988 (응답하라 1988)", "year": "2015", "type": "Drama", "desc": "공동체와 관계의 가치를 따뜻하게 그려낸 작품.", "link": "https://search.naver.com/search.naver?query=응답하라+1988"},
    ],
    "ENTJ": [
        {"title": "Inside Men (내부자들)", "year": "2015", "type": "Film", "desc": "권력, 전략, 정치적 게임을 즐기는 리더형에게 적합한 영화.", "link": "https://search.naver.com/search.naver?query=내부자들"},
        {"title": "The King's Letters? (말모이) — 리더와 비전의 이야기", "year": "2019", "type": "Film", "desc": "목표 지향적이고 큰 흐름을 보는 타입에게 추천.", "link": "https://search.naver.com/search.naver?query=말모이"},
    ],
}

# --- UI: MBTI button grid ---
mbti_list = list(RECS.keys())
cols = st.columns([1,8,1])
with cols[1]:
    st.markdown('<div class="mbti-grid">', unsafe_allow_html=True)
    chosen = st.selectbox("원하는 MBTI를 선택하세요:", options=["-- 선택 --"]+mbti_list, index=0)
    st.markdown('</div>', unsafe_allow_html=True)

# --- show recommendations ---
if chosen and chosen != "-- 선택 --":
    st.markdown(f"<h2 style='color:#fff; text-align:center; margin-top:8px'>✨ {chosen}에게 어울리는 작품</h2>", unsafe_allow_html=True)
    rows = []
    recs = RECS.get(chosen, [])
    for i, r in enumerate(recs):
        if i % 3 == 0:
            cols = st.columns(3)
        with cols[i % 3]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"<div class='movie-title'>{r['title']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='movie-meta'>{r['type']} · {r['year']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='movie-desc'>{r['desc']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:8px'><a class='link' href='{r['link']}' target='_blank'>🔎 더 보기</a></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

else:
    st.markdown('<div style="text-align:center; color:rgba(255,255,255,0.8);">MBTI를 선택하면 추천이 나타납니다 — 왼쪽에서 골라보세요.</div>', unsafe_allow_html=True)

# --- footer ---
st.markdown("""
<div style='text-align:center; padding-top:18px; color:rgba(255,255,255,0.6)'>
Made with ⚡ by Yerin · 원하면 포스터/애니메이션/개인 취향 반영해서 업그레이드해줄게요.
</div>
""", unsafe_allow_html=True)
