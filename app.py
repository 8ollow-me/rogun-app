from collections import deque
from datetime import datetime
from random import randint
from PIL import ImageFile

import streamlit as st
import pandas as pd
import cv2 as cv

import shutil
import os

from src.img_capture import open_capture, close_capture, capture_frame
from src.inference import infer_image
from src.analysis import analyse_daily_activity, analyse_total_activity
from src.utils import get_dataframe_row, image_to_base64
from src.gif import make_gif

ImageFile.LOAD_TRUNCATED_IMAGES = True

LOG_DIR = 'logs'
FRAME_DIR = 'frames'
CAPTURE_DIR = 'captures'
BBOX_DIR = 'bbox'

PLACEHOLDER = 'resources/placeholder.png'
CAM_BLIND = 'resources/cam_blind.png'
SOURCE_VIDEO = 'resources/demo.mp4'

BEEPS = {
    '알림음 끄기': '',
    '기본 알림음': 'https://www.soundjay.com/buttons/sounds/beep-07a.mp3',
    '멍멍': 'https://t1.daumcdn.net/cfile/tistory/99CC98395CE6F54B0A'
}
BEHAVIORS = ['FEETUP', 'SIT', 'WALK', 'LYING', 'BODYSHAKE']
NODOG = '강아지 없음'


os.makedirs(BBOX_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(CAPTURE_DIR, exist_ok=True)


def load_logs(log_dir='logs/'):
    logs = []
    for i, file_name in enumerate(os.listdir(log_dir)):
        df = pd.read_csv(os.path.join(log_dir, file_name))
        logs.append(df)
    if not logs:
        logs.append(pd.DataFrame(columns=['날짜', '시간', '행동']))
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
    st.session_state.behavior = NODOG
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
    
if 'demo_cap' not in st.session_state:
    st.session_state.demo_cap = open_capture(SOURCE_VIDEO)
if 'live_cap' not in st.session_state:
    # st.session_state.live_cap = open_capture(0)
    st.session_state.live_cap = st.session_state.demo_cap

if 'frames' not in st.session_state:
    frames = os.listdir(FRAME_DIR)
    for i in range(len(frames)):
        frame = frames[i]
        timestamp = datetime.strptime(frame[:-4], r'%Y-%m-%d %H_%M_%S_%f')
        frames[i] = (os.path.join(FRAME_DIR, frame), timestamp)
    frames = deque(frames)
    st.session_state.frames = frames
if 'bbox_frames' not in st.session_state:
    bbox_frames = os.listdir(BBOX_DIR)
    for i in range(len(bbox_frames)):
        file_path = bbox_frames[i]
        file_name = os.path.basename(file_path)
        if len(file_name[:-4].split(maxsplit=3)) != 4:
            continue
        d, t, has_dog, behavior = file_name[:-4].split(maxsplit=3)
        timestamp = datetime.strptime(f'{d} {t}', r'%Y-%m-%d %H_%M_%S_%f')
        bbox_frames[i] = (file_path, timestamp, has_dog, behavior)
    bbox_frames = deque(bbox_frames)
    st.session_state.bbox_frames = bbox_frames
if 'is_demo' not in st.session_state:
    st.session_state.is_demo = True
if 'gif_queue' not in st.session_state:
    st.session_state.gif_queue = deque()


def add_log(tiemstamp, behavior, image_path, notify=True):
    row = get_dataframe_row(tiemstamp.date(), tiemstamp.time(), behavior, image_path)
    if st.session_state.log.empty or st.session_state.log.iloc[0]['날짜'] == row.iloc[0]['날짜']:
        st.session_state.log = pd.concat([row, st.session_state.log], ignore_index=True)
    else:
        st.session_state.logs.insert(0, st.session_state.log)
        st.session_state.log = row
    if not st.session_state.log.empty:
        st.session_state.log.to_csv(os.path.join(LOG_DIR, st.session_state.log.iloc[0]['날짜'] + '.csv'), index=False)
    if notify and behavior in st.session_state.noti_filter:
        st.html(
            f'<audio autoplay><source src="{BEEPS[st.session_state.beep]}" type="audio/mpeg"></audio>'
        )
        st.toast(f'행동이 감지되었습니다: {behavior}', icon='🐶')
    st.session_state.behavior = behavior


"""
프래그먼트 생성
"""


@st.fragment(run_every='100ms')
def realtime_image():
    if st.session_state.is_cam_on:
        image = ''
        if frames := os.listdir(FRAME_DIR):
            image = os.path.join(FRAME_DIR, frames[-1])
        if not os.path.exists(image):
            image = PLACEHOLDER
    else:
        image = CAM_BLIND
    st.image(image, use_container_width=True)


@st.fragment(run_every='100ms')
def dataframe_brief():
    st.dataframe(
        st.session_state.log.head(10), 
        use_container_width=True, hide_index=True,
        column_config={
            '파일': st.column_config.LinkColumn(display_text="탐색기에서 열기")
        }
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
                    df, 
                    use_container_width=True, hide_index=True, key=date,
                    column_config={
                        '파일': st.column_config.LinkColumn(display_text="탐색기에서 열기")
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
            shutil.copy(image, CAPTURE_DIR)
            add_log(timestamp, st.session_state.behavior, os.path.join(CAPTURE_DIR, os.path.basename(image)), notify=False)
            st.toast('캡쳐된 이미지가 저장되었습니다.', icon='📸')
    with col4:
        st.button('저장소 열기', icon='📂', use_container_width=True)


@st.fragment(run_every='100ms')
def mic_info():
    if st.session_state.is_mic_on:
        st.info('마이크가 켜져있습니다!', icon='🎙️')
    else:
        st.empty()


@st.fragment(run_every='5s')
def analysis():
    df = analyse_total_activity([st.session_state.log] + st.session_state.logs)
    cur = df.iloc[len(df) - 1]
    
    if -5.0 <= cur['활동량 변화'] <= 5.0:
        delta_str = '전날과 비교했을 때 활동량에 큰 변화가 없습니다.'
    elif cur['활동량 변화'] > 5.0:
        delta_str = '전날에 비해 활동량이 증가했습니다.'
    else:
        delta_str = '전날에 비해 활동량이 감소했습니다.'
    
    st.metric(
        cur['날짜'], 
        value=f'{cur['활동량']:.1f} %', 
        delta=f'{cur['활동량 변화']:.1f} %', 
    )
    st.caption(delta_str)
    st.line_chart(df, x='날짜', y='활동량', x_label='', y_label='', height=300)


"""
뷰 배치
"""

st.set_page_config(
    page_title='로건 - 반려견 행동 분석',
    layout='wide'
)
tab_realtime, tab_log, tab_config = st.tabs(['🔴 실시간 영상', '📋 전체 행동 기록', '⚙️ 설정'])

with tab_realtime:
    # col1, col2 = st.columns([6, 4])
    # with col1:
    toolbar()
    realtime_image()
    # with col2:
    #     dataframe_brief()
    #     st.caption('최근에 기록된 행동이 10개까지 표시됩니다.')
    mic_info()
    
with tab_log:
    mic_info()
    col1, col2 = st.columns([1, 4])
    with col1:
        realtime_image()
        st.markdown('##### 활동량 변화')
        analysis()
    with col2:
        st.markdown('### 행동 기록')
        st.session_state.log_filter = st.multiselect(
            label='검색 필터',
            options=[NODOG] + BEHAVIORS,
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
        st.session_state.is_demo = st.toggle('시연 모드', value=True)

"""
작업 코루틴
"""


@st.fragment(run_every='100ms')
def take_frame():
    frames = st.session_state.frames
    demo_cap = st.session_state.demo_cap
    live_cap = st.session_state.live_cap
    
    frame, timestamp = capture_frame(demo_cap if st.session_state.is_demo else live_cap, FRAME_DIR)
    if frame is None:
        return
    frames.append((frame, timestamp))
take_frame()


@st.fragment(run_every='1s')
def infer():
    frames = st.session_state.frames
    bbox_frames = st.session_state.bbox_frames
    gif_queue = st.session_state.gif_queue
    
    if bbox_frames and isinstance(bbox_frames[-1], tuple):
        _, _, has_dog, behavior = bbox_frames[-1]
    else:
        has_dog = False
        behavior = NODOG
    
    if not frames:
        return
    
    frame, timestamp = frames[-1]
    
    # result = infer_image(frame, has_dog, behavior)
    result = {'bbox_image_path': '_', 'has_dog': True, 'current_class': 'WALK', 'make_gif': False}
    print(f'infer: {result}')
    bbox_image = result['bbox_image_path']
    has_dog = result['has_dog']
    behavior = result['current_class']
    need_gif = result['make_gif']
    
    bbox_frames.append((bbox_image, timestamp, has_dog, behavior))
    
    if need_gif:
        gif_name = f'{timestamp.strftime(r'%Y-%m-%d %H_%M_%S_%f')}.gif'
        gif_queue.append((gif_name, timestamp))
        add_log(timestamp, behavior, os.path.join(CAPTURE_DIR, gif_name))
    
    st.session_state.behavior = behavior
infer()


@st.fragment(run_every='1s')
def gif():
    gif_queue = st.session_state.gif_queue
    print(f'@@@ gif: {gif_queue}')
    DURATION = 10
    
    if not gif_queue:
        return
    
    gif_name, timestamp = gif_queue[0]
    while (datetime.now() - timestamp).total_seconds() > DURATION // 2:
        make_gif(BBOX_DIR, CAPTURE_DIR, gif_name, 10 * DURATION)
        gif_queue.popleft()
        if not gif_queue:
            break
        gif_name, timestamp = gif_queue[0]
gif()


@st.fragment(run_every='1s')
def remove_old_frame():
    print(f'@@@ remove_old_frame')
    frames = st.session_state.frames
    bbox_frames = st.session_state.bbox_frames
    
    while len(frames) > 1000:
        to_remove, _ = frames[0]
        if os.path.exists(to_remove):
            try:
                os.remove(to_remove)
            except Exception as e:
                print(e)
                continue
        frames.popleft()

    while len(bbox_frames) > 1000:
        to_remove, _, _, _ = bbox_frames[0]
        if os.path.exists(to_remove):
            try:
                os.remove(to_remove)
            except Exception as e:
                print(e)
                continue
        bbox_frames.popleft()
remove_old_frame()
