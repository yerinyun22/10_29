import streamlit as st
st.title('예린의 첫번째 앱')
st.subheader('아')
st.write('ㅠ')
st.link_button('네이버','https://naver.com')

name=st.text_input('이름')
if st.button("가나디"):
    st.write(name,'안녕')
    st.balloons()
    

st.success('win!!!')
st.warning('zz')
st.info('?')
