import cv2 as cv
import os
from datetime import datetime
import time

def capture_frame(cap, save_folder='captured_frames', frame_size=(608, 608)):
    # 저장할 폴더 경로 설정
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    ret, frame = cap.read()
    
    if not ret:
        print('프레임에 실패하여 루프를 나갑니다.')
        return

    # 프레임 캡처 및 리사이즈
    resized_frame = cv.resize(frame, frame_size)
    
    # 현재 시간을 파일 이름으로 설정 (밀리초 포함)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    frame_path = os.path.join(save_folder, f'{timestamp}.jpg')
    
    # 이미지 저장
    cv.imwrite(frame_path, resized_frame)
    print(f'프레임이 {frame_path}에 저장되었습니다.')

    return frame_path

# VideoCapture 객체를 반복문 외부에서 생성
cap = cv.VideoCapture(0, cv.CAP_DSHOW)

if not cap.isOpened():
    print('카메라 연결 실패')
else:
    # 5초 동안 실행하되, 0.1초에 한 번씩 capture_frame 함수를 호출하는 코드
    start_time = time.time()
    while time.time() - start_time < 5:
        capture_frame(cap)
        time.sleep(0.1)

    cap.release()