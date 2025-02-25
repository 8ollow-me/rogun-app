from torchvision import models
from ultralytics import YOLO
from PIL import Image

import pandas as pd
import numpy as np
import shutil
import time
import cv2
import os

import torch
import torch.nn as nn
import torchvision.transforms as transforms

torch.classes.__path__ = []

# ------------------------
# 1. 환경 설정
# ------------------------
NODOG = '강아지 없음'
BBOX_DIR = 'bbox'
os.makedirs(BBOX_DIR, exist_ok=True)

# ------------------------
# 2. YOLO 모델 로드 (강아지 탐지)
# ------------------------
yolo_model = YOLO("resources/yolo11m.pt")

# ------------------------
# 3. ResNet 모델 로드 (강아지 동작 분류)
# ------------------------
device = 'cuda' if torch.cuda.is_available() else 'cpu'
resnet_model = models.resnet18(weights=None)
num_features = resnet_model.fc.in_features
num_classes = 10
resnet_model.fc = nn.Linear(num_features, num_classes)
resnet_model.load_state_dict(torch.load("resources/resnet18.pth", map_location=device))
resnet_model.to(device)
resnet_model.eval()

# ------------------------
# 4. 이미지 전처리 함수 (ResNet 입력용)
# ------------------------
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# ------------------------
# 5. 바운딩 박스 그리기 (YOLO + ResNet)
# ------------------------
def draw_bounding_box(frame, x1, y1, x2, y2, class_name):
    """
    바운딩 박스를 그리고, 클래스명 + ID를 표시하는 함수.

    Args:
        frame (numpy.ndarray): 원본 이미지
        x1, y1, x2, y2 (int): 바운딩 박스 좌표
        class_name (str): 예측된 클래스명
        object_id (int): 객체 ID

    Returns:
        frame (numpy.ndarray): 바운딩 박스가 추가된 이미지
    """
    class_colors = {
        "SIT": (0, 255, 255),
        "WALK": (0, 255, 0),
        "LYING": (255, 0, 255),
        "BODYSHAKE": (255, 0, 0),
        "FEETUP": (0, 0, 255)
    }
    bbox_color = class_colors.get(class_name, (192, 192, 192))

    cv2.rectangle(frame, (x1, y1), (x2, y2), bbox_color, 2)

    label = f"{class_name}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 2
    font_thickness = 2
    text_size = cv2.getTextSize(label, font, font_scale, font_thickness)[0]
    text_w, text_h = text_size
    text_x, text_y = x1, y1 - 5 if y1 > 20 else y1 + 20

    cv2.rectangle(frame, (text_x, text_y - text_h - 4), (text_x + text_w + 4, text_y), bbox_color, -1)
    cv2.putText(frame, label, (text_x + 2, text_y - 2), font, font_scale, (0, 0, 0), font_thickness, cv2.LINE_AA)
    
    return frame

# ------------------------
# 6. 이미지 추론 함수 (YOLO + ResNet)
# ------------------------
def infer_image(image_path, prev_has_dog, prev_class):
    """
    입력 이미지에서 강아지를 감지하고 동작을 분류하는 함수.

    Returns:
        dict: 결과 정보 (바운딩 박스 이미지 경로, 강아지 존재 여부, 현재 동작, GIF 생성 여부)
    """
    global yolo_model
    
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"❌ 이미지 로드 실패: {image_path}")
        return {"has_dog": prev_has_dog, "current_class": prev_class, "make_gif": False}
    
    # 우선 목적지에 원본 이미지를 복제
    shutil.copy(image_path, BBOX_DIR)
    image_path = os.path.join(BBOX_DIR, os.path.basename(image_path))
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 1️⃣ YOLO 탐지
    results = yolo_model(frame_rgb)
    best_box = None
    best_confidence = 0.0

    for result in results:
        for box in result.boxes.data:
            x1, y1, x2, y2, conf, cls = box.tolist()
            if int(cls) == 16 and conf > best_confidence:
                best_confidence = conf
                best_box = (int(x1), int(y1), int(x2), int(y2))

    # 2️⃣ 강아지가 없는 경우 처리
    if best_box is None:
        print('👁️‍🗨️ 강아지가 없습니다.')
        new_image_path = f'{image_path[:-4]} False 강아지 없음.jpg'
        if not os.path.exists(new_image_path):
            os.rename(image_path, new_image_path)
        else:
            os.remove(image_path)
        return {"bbox_image_path": image_path, "has_dog": False, "current_class": NODOG, "make_gif": prev_has_dog}

    # 3️⃣ 강아지 영역 크롭 후 ResNet으로 분류
    x1, y1, x2, y2 = best_box
    cropped_img = frame_rgb[y1:y2, x1:x2]
    cropped_img_pil = Image.fromarray(cropped_img)
    processed_img = transform(cropped_img_pil).unsqueeze(0)

    with torch.no_grad():
        start_time = time.time()
        outputs = resnet_model(processed_img.to(device))
        end_time = time.time()
        probs = torch.softmax(outputs, dim=1)
        predicted_class = torch.argmax(probs, dim=1).item()
        confidence = probs[0, predicted_class].item()

    current_class = ["BODYLOWER", "BODYSCRATCH", "BODYSHAKE", "FEETUP", "FOOTUP", "LYING", "MOUNTING", "SIT", "TURN", "WALKRUN"][predicted_class]

    # 추론 시간 계산 (ms 단위)
    inference_time_ms = (end_time - start_time) * 1000
    print(f"Speed: {inference_time_ms:.2f}ms for ResNet")

    # 4️⃣ 바운딩 박스 그리기 (현재 클래스 적용)
    frame = draw_bounding_box(frame, x1, y1, x2, y2, current_class)
    cv2.imwrite(image_path, frame)

    # 5️⃣ 이전 클래스와 비교하여 GIF 생성 여부 결정
    print(f'👁️‍🗨️ 추론 결과: {current_class}')
    new_image_path = f'{image_path[:-4]} True {current_class}.jpg'
    if not os.path.exists(new_image_path):
        os.rename(image_path, new_image_path)
    else:
        os.remove(image_path)
    return {"bbox_image_path": image_path, "has_dog": True, "current_class": current_class, "make_gif": prev_class != current_class}
