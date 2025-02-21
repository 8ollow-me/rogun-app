import base64
import pandas as pd
from io import BytesIO
from PIL import Image


def image_to_base64(filepath: str) -> str:
    with open(filepath, "rb") as f:
        image = Image.open(f)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{b64_data}"


def get_dataframe_row(date, time, behavior, image_path):
    return pd.DataFrame({'날짜': [date.strftime(r'%Y년 %m월 %d일')], '시간': [time.strftime(r'%H시 %M분 %S초')], '행동': [behavior], '캡쳐': [image_path]})