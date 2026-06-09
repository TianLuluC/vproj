import cv2
import numpy as np

def is_bad_frame(current_frame, prev_frame, 
                 diff_threshold=35.0, 
                 var_threshold=2800, 
                 gray_threshold=0.85, 
                 local_noise_threshold=1800, 
                 freeze_threshold=0.92):
    """检测雪花、灰屏、局部乱码及画面冻结等异常帧"""
    if prev_frame is None or current_frame.shape != prev_frame.shape:
        return False

    h, w = current_frame.shape[:2]
    gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray, prev_gray)
    mean_diff = np.mean(diff.astype(np.float32))
    var = np.var(gray.astype(np.float32))

    mean_color = np.mean(current_frame, axis=(0,1))
    color_range = np.max(current_frame) - np.min(current_frame)
    gray_ratio = np.sum(np.abs(current_frame.astype(np.float32) - mean_color) < 20) / (h * w * 3)
    is_gray_screen = (color_range < 40) or (gray_ratio > gray_threshold)

    lap = cv2.Laplacian(gray, cv2.CV_64F)
    local_var = np.var(lap)
    is_local_noise = local_var > local_noise_threshold

    if not hasattr(is_bad_frame, 'freeze_counter'):
        is_bad_frame.freeze_counter = 0

    ssim_like = 1 - np.mean(np.abs(gray - prev_gray)) / 255.0
    if ssim_like > freeze_threshold:
        is_bad_frame.freeze_counter += 1
    else:
        is_bad_frame.freeze_counter = 0

    bad = False
    if mean_diff > diff_threshold: bad = True
    if var > var_threshold: bad = True
    if is_gray_screen: bad = True
    if is_local_noise and not is_gray_screen: bad = True
    if is_bad_frame.freeze_counter >= 3: bad = True

    return bad