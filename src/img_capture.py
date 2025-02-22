import cv2 as cv
import os
from datetime import datetime


def open_capture():
    return cv.VideoCapture(0, cv.CAP_DSHOW)


def close_capture(cap):
    return cap.release()


def capture_frame(cap, target_dir='frames', image_name=None):
    os.makedirs(target_dir, exist_ok=True)
    now = datetime.now()
    ret, frame = cap.read()
    if not ret:
        return None, now

    if image_name is None:
        image_name = datetime.now().strftime(r"%Y-%m-%d %H_%M_%S_%f")
    file_name = os.path.join(target_dir, f'{image_name}.jpg')
    if cv.imwrite(file_name, frame):
        return file_name, now