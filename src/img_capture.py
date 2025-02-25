import cv2 as cv
import os
from datetime import datetime


def open_capture(src=0):
    if src == 0:
        return cv.VideoCapture(0, cv.CAP_DSHOW)
    return cv.VideoCapture(src)


def close_capture(cap: cv.VideoCapture):
    cap.release()


def capture_frame(cap, target_dir='frames', image_name=None):
    os.makedirs(target_dir, exist_ok=True)
    ret, frame = cap.read()
    now = datetime.now()
    if not ret:
        cap.set(cv.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        now = datetime.now()

    if image_name is None:
        image_name = datetime.now().strftime(r"%Y-%m-%d %H_%M_%S_%f")
    file_name = os.path.join(target_dir, f'{image_name}.jpg')
    if cv.imwrite(file_name, frame):
        return file_name, now