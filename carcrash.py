import streamlit as st
import pandas as pd
import numpy as np

# Google Drive 링크 → 직접 다운로드 링크
GOOGLE_DRIVE_ID = "1c3ULCZImSX4ns8F9cIE2wVsy8Avup8bu"
CSV_URL = f"https://drive.google.com/uc?export=download&id={GOOGLE_DRIVE_ID}"

@st.cache_data
def load_data(url=CSV_URL):
    try:
        df = pd.read_csv(url, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(url, encoding="cp949")
    df.columns = [c.strip() for c in df.columns]  # 컬럼 공백 제거
    return df

# 데이터 로드
data = load_data()
st.write("데이터 미리보기:", data.head())
