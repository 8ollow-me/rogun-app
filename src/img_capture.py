import cv2 as cv
import os
from datetime import datetime


def capture_start():
    return cv.VideoCapture(0, cv.CAP_DSHOW)


def capture_finish(cap):
    return cap.release()


def capture_frame(cap, target_dir='frames', image_name=None):
    os.makedirs(target_dir, exist_ok=True)
    ret, frame = cap.read()
    if not ret:
        return

    if image_name is None:
        image_name = datetime.now().strftime(r"%Y년 %m월 %d일 %H시 %M분 %S초 %f")
    file_name = os.path.join(target_dir, f'{image_name}.jpg')
    cv.imwrite(file_name, frame)
    return file_name