import os
import imageio


def make_gif(src_dir, dest_dir, file_name, frame_num):
    all_images = os.listdir(src_dir)
    if not all_images:
        print(f"⚠️ 이미지가 없습니다.")
        return None

    os.makedirs(dest_dir, exist_ok=True)
    gif_path = os.path.join(dest_dir, file_name)

    with imageio.get_writer(gif_path, mode='I', duration=0.99) as writer:
        for image_name in all_images[-frame_num:]:
            img = imageio.imread(os.path.join(src_dir, image_name))
            writer.append_data(img)

    return gif_path
