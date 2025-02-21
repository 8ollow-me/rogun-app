from datetime import datetime
from random import randint
import streamlit as st
import pandas as pd
import os
import cv2 as cv

from src.utils import get_dataframe_row, image_to_base64
from src.img_capture import capture_start, capture_finish, capture_frame

PLACEHOLDER = 'resources/placeholder.png'
BEEPS = {
    '알림음 끄기': '',
    '기본 알림음': 'https://www.soundjay.com/buttons/sounds/beep-07a.mp3',
    '멍멍': 'https://t1.daumcdn.net/cfile/tistory/99CC98395CE6F54B0A'
}
BEHAVIORS = [
    "BODYLOWER", "BODYSCRATCH", "BODYSHAKE", "FEETUP", "FOOTUP",
    "HEADING", "LYING", "MOUNTING", "SIT", "TAILING",
    "TAILLOW", "TURN", "WALKRUN"
]
NONE = '행동 없음'


def load_logs(log_dir='logs/'):
    logs = []
    for file_name in os.listdir(log_dir):
        df = pd.read_csv(os.path.join(log_dir, file_name))
        df['캡처'] = df['캡처'].apply(image_to_base64)
        logs.append(df)
    if not logs:
        logs.append(pd.DataFrame(columns=['날짜', '시간', '행동', '캡처']))
    log = logs.pop()
    logs.reverse()
    return log, logs


"""
상태 생성
"""
if 'placeholder' not in st.session_state:
    st.session_state.placeholder = 0 
if 'log' not in st.session_state:
    st.session_state.log, st.session_state.logs = load_logs()
if 'behavior' not in st.session_state:
    st.session_state.behavior = NONE
if 'beep' not in st.session_state:
    st.session_state.beep = list(BEEPS.keys())[1]
if 'noti_filter' not in st.session_state:
    st.session_state.noti_filter = []
if 'log_filter' not in st.session_state:
    st.session_state.log_filter = []
if 'toasts' not in st.session_state:
    st.session_state.toasts = []
if 'cam' not in st.session_state:
    st.session_state.cam = capture_start()

"""
프래그먼트 생성
"""
@st.fragment(run_every='33ms')
def image1():
    image = capture_frame(st.session_state.cam, image_name='temp')
    st.image(image or PLACEHOLDER, use_container_width=True)


@st.fragment(run_every='33ms')
def image2():
    image = capture_frame(st.session_state.cam, image_name='temp')
    st.image(image or PLACEHOLDER, use_container_width=True)


@st.fragment(run_every='33ms')
def image3():
    image = capture_frame(st.session_state.cam, image_name='temp')
    st.image(image or PLACEHOLDER, use_container_width=True)


@st.fragment(run_every='100ms')
def dataframe_brief():
    st.dataframe(
        st.session_state.log.head(10), use_container_width=True, hide_index=True,
        column_config={'캡처': st.column_config.ImageColumn('캡처')}
    )


@st.fragment(run_every='100ms')
def dataframe_of_day():
    has_no_data = True
    is_first = True
    for df in [st.session_state.log] + st.session_state.logs:
        if st.session_state.log_filter:
            df = df[df['행동'].isin(st.session_state.log_filter)]
        if df.empty:
            continue
        has_no_data = False
        with st.expander(df.iloc[0]['날짜'], expanded=is_first):
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_config={'캡처': st.column_config.ImageColumn('캡처')}
            )
        is_first = False
    if has_no_data:
        st.caption('행동 기록이 없습니다.')
    

"""
뷰 배치
"""
st.set_page_config(
    page_title='로건 - 반려견 행동 분석',
    layout='wide'
)
tab_realtime, tab_log, tab_config = st.tabs(['🔴 실시간 영상', '📋 행동 기록', '⚙️ 설정'])

with tab_realtime:
    col1, col2 = st.columns([6, 4])
    with col1:
        image1()
    with col2:
        dataframe_brief()
    
with tab_log:
    col1, col2 = st.columns([1, 4])
    with col1:
        image2()
    with col2:
        st.markdown('### 행동 기록')
        st.session_state.log_filter = st.multiselect(
            label='검색 필터',
            options=[NONE] + BEHAVIORS,
            placeholder='검색 조건을 추가하세요.'
        )
        dataframe_of_day()

with tab_config:
    col1, col2 = st.columns([1, 4])
    with col1:
        image3()
    with col2:
        st.markdown('### 알림 설정')
        st.session_state.noti_filter = st.multiselect(
            label='반려견이 특정 행동을 했을 때 알림을 받습니다.',
            options=BEHAVIORS,
            placeholder='알림을 받을 행동을 선택하세요.'
        )
        with st.expander('알림음 설정'):
            st.session_state.beep = st.radio(
                label='알림음 설정', 
                options=list(BEEPS.keys()),
                index=1,
                label_visibility='collapsed'
            )
            if st.session_state.beep:
                st.html(
                    f'<audio autoplay><source src="{BEEPS[st.session_state.beep]}" type="audio/mpeg"></audio>'
                )


if st.button('테스트'):
    now = datetime.now()
    if st.session_state.behavior == NONE:
        behavior = BEHAVIORS[randint(0, len(BEHAVIORS) - 1)]
    else:
        behavior = NONE
    row = get_dataframe_row(now.date(), now.time(), behavior, PLACEHOLDER)
    st.session_state.log = pd.concat([row, st.session_state.log], ignore_index=True)

    if behavior in st.session_state.noti_filter:
        st.html(
            f'<audio autoplay><source src="{BEEPS[st.session_state.beep]}" type="audio/mpeg"></audio>'
        )
        st.session_state.toasts.append(
           st.toast(f'행동이 감지되었습니다: {behavior}', icon='🐶')
        )
    st.session_state.behavior = behavior
