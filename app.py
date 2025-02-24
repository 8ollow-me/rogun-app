from collections import deque
from datetime import datetime
from random import randint
import streamlit as st
import pandas as pd
import cv2 as cv
import threading
import shutil
import time
import os

from src.img_capture import open_capture, close_capture, capture_frame
from src.utils import get_dataframe_row, image_to_base64

FRAME_DIR = 'frames'
CAPTURE_DIR = 'captures'
PLACEHOLDER = 'resources/placeholder.png'
BEEPS = {
    '알림음 끄기': '',
    '기본 알림음': 'https://www.soundjay.com/buttons/sounds/beep-07a.mp3',
    '멍멍': 'https://t1.daumcdn.net/cfile/tistory/99CC98395CE6F54B0A'
}
BEHAVIORS = ['FEETUP', 'SIT', 'WALK', 'LYING', 'BODYSHAKE']
NONE = '행동 없음'

os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(CAPTURE_DIR, exist_ok=True)

frames = os.listdir(FRAME_DIR)
for i in range(len(frames)):
    frame = frames[i]
    timestamp = datetime.strptime(frame[:-4], r'%Y-%m-%d %H_%M_%S_%f')
    frames[i] = (os.path.join(FRAME_DIR, frame), timestamp)
frames = deque(frames)


def load_logs(log_dir='logs/'):
    logs = []
    for file_name in os.listdir(log_dir):
        df = pd.read_csv(os.path.join(log_dir, file_name))
        df['캡처'] = df['캡처'].apply(image_to_base64, format='gif')
        logs.append(df)
    if not logs:
        logs.append(pd.DataFrame(columns=['날짜', '시간', '행동', '캡처']))
    log = logs.pop()
    logs.reverse()
    return log, logs


def add_log(tiemstamp, behavior, image_path, notify=True):
    row = get_dataframe_row(tiemstamp.date(), tiemstamp.time(), behavior, image_path)
    if st.session_state.log.empty or st.session_state.log.iloc[0]['날짜'] == row.iloc[0]['날짜']:
        st.session_state.log = pd.concat([row, st.session_state.log], ignore_index=True)
    else:
        st.session_state.logs.insert(0, st.session_state.log)
        st.session_state.log = row 
    
    if notify and behavior in st.session_state.noti_filter:
        st.html(
            f'<audio autoplay><source src="{BEEPS[st.session_state.beep]}" type="audio/mpeg"></audio>'
        )
        st.toast(f'행동이 감지되었습니다: {behavior}', icon='🐶')
    st.session_state.behavior = behavior


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
if 'log_expanded' not in st.session_state:
    st.session_state.log_expanded = {}
if 'is_mic_on' not in st.session_state:
    st.session_state.is_mic_on = False
if 'is_cam_on' not in st.session_state:
    st.session_state.is_cam_on = True
if 'is_demo' not in st.session_state:
    st.session_state.is_demo = True

"""
프래그먼트 생성
"""
@st.fragment(run_every='1ms')
def realtime_image():
    if st.session_state.is_demo:
        if st.session_state.is_cam_on:
            image = PLACEHOLDER
        else:
            image = PLACEHOLDER
    elif st.session_state.is_cam_on:
        image = ''
        if frames := os.listdir(FRAME_DIR):
            image = os.path.join(FRAME_DIR, frames[-1])
        if not os.path.exists(image):
            image = PLACEHOLDER
    else:
        image = PLACEHOLDER
    st.image(image, use_container_width=True)


@st.fragment(run_every='100ms')
def dataframe_brief():
    st.dataframe(
        st.session_state.log.head(10), use_container_width=True, hide_index=True,
        column_config={'캡처': st.column_config.ImageColumn('캡처')}
    )


@st.fragment(run_every='100ms')
def entire_dataframes():
    has_no_data = True
    is_first = True
    logs = [st.session_state.log] + st.session_state.logs
    with st.container():
        for df in logs:
            if st.session_state.log_filter:
                df = df[df['행동'].isin(st.session_state.log_filter)]
            if df.empty:
                continue
            has_no_data = False
            
            date = df.iloc[0]['날짜']
            if date not in st.session_state.log_expanded:
                st.session_state.log_expanded[date] = is_first
            is_first = False
            
            with st.expander(date, expanded=st.session_state.log_expanded[date]):
                st.dataframe(
                    df, use_container_width=True, hide_index=True, key=date,
                    column_config={
                        '날짜': st.column_config.Column(width='small'),
                        '시간': st.column_config.Column(width='small'),
                        '행동': st.column_config.Column(width='small'),
                        '캡처': st.column_config.ImageColumn('캡처', width='large')
                    }
                )
        if has_no_data:
            st.caption('행동 기록이 없습니다.')


@st.fragment()
def toolbar():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.session_state.is_mic_on = st.toggle(
            '🎙️ 마이크', 
            value=False, 
            help='실시간으로 전달된 음성이 홈캠의 스피커에서 재생됩니다.'
        )
    with col2:
        st.session_state.is_cam_on = st.toggle(
            '📹 카메라', 
            value=True, 
            help='화면에서 실시간 카메라 화면이 가려지지만, 녹화와 분석은 계속 진행됩니다.'
        )
    with col3:
        if st.button('캡쳐하기', icon='📸', use_container_width=True) and frames:
            image, timestamp = frames[-1]
            add_log(timestamp, st.session_state.behavior, image, notify=False)
            shutil.copy(image, CAPTURE_DIR)
            st.toast('캡쳐된 이미지가 저장되었습니다.', icon='📸')
    with col4:
        if st.button('저장소 열기', icon='📂', use_container_width=True):
            os.startfile(CAPTURE_DIR, 'open')


@st.fragment(run_every='100ms')
def mic_info():
    if st.session_state.is_mic_on:
        st.info('마이크가 켜져있습니다!', icon='🎙️')
    else:
        st.empty()


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
        realtime_image()
        toolbar()
    with col2:
        dataframe_brief()
    mic_info()
    
with tab_log:
    mic_info()
    col1, col2 = st.columns([1, 4])
    with col1:
        realtime_image()
    with col2:
        st.markdown('### 행동 기록')
        st.session_state.log_filter = st.multiselect(
            label='검색 필터',
            options=[NONE] + BEHAVIORS,
            placeholder='검색 조건을 추가하세요.'
        )
        entire_dataframes()

with tab_config:
    col1, col2 = st.columns([1, 4])
    with col1:
        realtime_image()
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
        st.markdown('### 접근성 설정')
        st.session_state.is_demo = st.toggle('시연 모드', True)


"""
작업 스레드
"""
def take_frame():
    global frames
    
    cap = open_capture()
    while True:
        frame, timestamp = capture_frame(cap, FRAME_DIR)
        if frame is None:
            continue
        frames.append((frame, timestamp))
        time.sleep(0.033)


def remove_old_frame(max_frame):
    global frames
    
    while True:
        while len(frames) > max_frame:
            to_remove, _ = frames[0]
            if os.path.exists(to_remove):
                try:
                    os.remove(to_remove)
                except Exception as e:
                    print(e)
                    continue
            frames.popleft()
        time.sleep(0.033)

threading.Thread(target=take_frame, daemon=True).start()
threading.Thread(target=remove_old_frame, args=(1000,), daemon=True).start()
