import os
import glob
import imageio

def save_behavior_change_gif(dir_path, frame_num):
    all_images = sorted(glob.glob(os.path.join(dir_path, "*.jpg")), key=os.path.getmtime)
    selected_images = all_images[-frame_num:]
    if len(selected_images) < frame_num:
        print(f"⚠️ 이미지가 {frame_num}장보다 적습니다! 현재 {len(selected_images)}장만 선택됨.")
        return None

    gif_dir = os.path.join(os.getcwd(), "gif_dir")
    os.makedirs(gif_dir, exist_ok=True)

    existing_gif_files = glob.glob(os.path.join(gif_dir, "behavior_change_*.gif"))
    gif_numbers = [int(f.split('_')[-1].split('.')[0]) for f in existing_gif_files if f.split('_')[-1].split('.')[0].isdigit()]
    
    if gif_numbers:
        next_number = max(gif_numbers) + 1
    else:
        next_number = 1

    gif_filename = f"behavior_change_{next_number}.gif"
    gif_path = os.path.join(gif_dir, gif_filename)

    with imageio.get_writer(gif_path, mode='I', duration=0.033) as writer:
        for img_path in selected_images:
            img = imageio.imread(img_path)
            writer.append_data(img)

    return gif_path
