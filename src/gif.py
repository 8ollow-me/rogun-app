import os
import glob
import imageio

def save_behavior_change_gif(dir_path, N):
    """
    디렉토리에서 가장 최근에 생성된 N장의 이미지를 사용하여 GIF 파일을 만들고 저장하는 함수.
    - dir_path: 이미지들이 저장된 디렉토리 경로
    - N: 사용할 이미지 장수

    반환값: 생성된 GIF 파일의 경로
    """
    # 디렉토리에서 모든 이미지 파일을 시간 순서대로 정렬하여 리스트로 가져오기
    all_images = sorted(glob.glob(os.path.join(dir_path, "*.jpg")), key=os.path.getmtime)

    # 가장 최근에 생성된 N개의 이미지 선택
    selected_images = all_images[-N:]
    
    if len(selected_images) < N:
        print(f"⚠️ 이미지가 {N}장보다 적습니다! 현재 {len(selected_images)}장만 선택됨.")
        return None

    # gif_dir 폴더 확인
    gif_dir = os.path.join(os.getcwd(), "gif_dir")
    os.makedirs(gif_dir, exist_ok=True)  # gif_dir 폴더가 없으면 생성

    # 기존 GIF 파일들의 숫자를 확인하여 가장 큰 번호를 찾아 다음 번호 생성(gif파일명 임시로 정함)
    existing_gif_files = glob.glob(os.path.join(gif_dir, "behavior_change_*.gif"))
    gif_numbers = [int(f.split('_')[-1].split('.')[0]) for f in existing_gif_files if f.split('_')[-1].split('.')[0].isdigit()]
    
    if gif_numbers:
        next_number = max(gif_numbers) + 1
    else:
        next_number = 1

    # 새로운 GIF 파일 이름 (behavior_change_1.gif, behavior_change_2.gif, ...)
    gif_filename = f"behavior_change_{next_number}.gif"
    gif_path = os.path.join(gif_dir, gif_filename)

    # 선택된 이미지를 imageio로 GIF에 저장
    with imageio.get_writer(gif_path, mode='I', duration=0.1) as writer:
        for img_path in selected_images:
            img = imageio.imread(img_path)  # 이미지를 읽어서 GIF에 추가
            writer.append_data(img)

    print(f"🎥 GIF 저장 완료: {gif_path}")
    return gif_path


# 예시: 디렉토리 'dog_images'에서 최근 10장의 이미지로 GIF 만들기
dir_path = "yolotest\\output_frames2"
N = 10
gif_path = save_behavior_change_gif(dir_path, N)
print(f"생성된 GIF 경로: {gif_path}")
