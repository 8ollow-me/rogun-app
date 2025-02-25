import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image


def image_to_base64(filepath: str, format='png') -> str:
    if not os.path.exists(filepath):
        return ''
    with open(filepath, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{format};base64,{b64_data}"


def get_dataframe_row(date, time, behavior, image):
    return pd.DataFrame({
        '날짜': [date.strftime(r'%Y년 %m월 %d일')], 
        '시간': [time.strftime(r'%H시 %M분 %S초 %f')], 
        '행동': [behavior],
        '파일': [image], 
    })