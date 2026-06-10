import os
import sys

# ========================================================
# 强制将当前 main.py 所在的绝对路径注入系统变量
# 注意：这里必须是 __file__，绝对不能写成 __name__
# ========================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ========================================================

import time
import cv2
import ctypes
import logging
import threading
import numpy as np
from PIL import ImageDraw, Image
from queue import Empty

from config import Config
from utils.hardware import find_available_gpu
from utils.bad_frame import is_bad_frame
from modules.regoin import RegionManager
from modules.stream import StreamManager
from modules.alert import AlertManager
from modules.detector import YoLo11TRT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("SafetyPipeline")

class SafetyPipeline:
    def __init__(self, config: Config):
        self.cfg = config
        self.stop_event = threading.Event()
        
        # 初始化第三方依赖
        ctypes.CDLL(self.cfg.PLUGIN_LIBRARY)
        
        gpu_id = find_available_gpu()
        if gpu_id == -1:
            logger.error("无可用显卡或显存不足 10%！程序终止。")
            sys.exit(1)
            
        # 模块化装载
        self.region_mgr = RegionManager(self.cfg)
        self.roi_coords = self.region_mgr.load_coordinates()
        
        self.stream_mgr = StreamManager(self.cfg, self.stop_event)
        self.alert_mgr = AlertManager(self.cfg)
        self.detector = YoLo11TRT(self.cfg.ENGINE_PATH, gpu_id)
        
        self.last_good_frame = None

    def _inference_loop(self):
        no_frame_cnt = 0
        while not self.stop_event.is_set():
            try:
                frame = self.stream_mgr.frame_queue.get(timeout=1.0)
                no_frame_cnt = 0
            except Empty:
                no_frame_cnt += 1
                if no_frame_cnt >= 180:
                    logger.error("🚨 超过 3 分钟未接收到任何视频流！触发超时，程序直接强制自杀结束。")
                    self.stop_event.set()
                    self.stream_mgr.release()
                    os._exit(1)
                elif no_frame_cnt % 10 == 0:
                    logger.warning(f"已 {no_frame_cnt} 秒未收到视频流，等待底层网络自愈...")
                continue

            detect_flag = False
            cls_ids = []
            
            image_raw, detect_flag, cls_ids = self.detector.infer(frame, self.roi_coords)         
            img_resized = cv2.resize(image_raw, (640, 360))
            img_pil = Image.fromarray(img_resized)
            draw = ImageDraw.Draw(img_pil)
            
            # --- 告警交管 ---
            img_pil = self.alert_mgr.process(img_pil, draw, detect_flag, cls_ids)
            
            # --- 推流写入 ---
            self.stream_mgr.write_frame(np.array(img_pil))

    def run(self):
        logger.info(f"🚀 启动安全监控流水线 | 摄像头: {self.cfg.C_NAME} | ID: {self.cfg.C_ID}")
        self.stream_mgr.start()
        
        try:
            self._inference_loop()
        except KeyboardInterrupt:
            logger.info("捕获到终止信号，准备退出...")
        finally:
            self.stop_event.set()
            self.stream_mgr.release()
            self.detector.destroy()
            logger.info("安资源已安全清理完毕。")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python main.py <RTSP_URL> <CAMERA_ID> <CAMERA_NAME>")
        sys.exit(1)
        
    cfg = Config(c_id=sys.argv[2], c_name=sys.argv[3], rtsp_addr=sys.argv[1])
    pipeline = SafetyPipeline(cfg)
    pipeline.run()