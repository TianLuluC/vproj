import os
import sys
import cv2

# ========================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ========================================================

import logging
import threading
from queue import Empty

from config import Config
from modules.stream import StreamManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("PassThroughPipeline")

class PassThroughPipeline:
    def __init__(self, config: Config):
        self.cfg = config
        self.stop_event = threading.Event()
        
        # 仅保留流媒体管理器
        self.stream_mgr = StreamManager(self.cfg, self.stop_event)

    def _transfer_loop(self):
        """纯粹的搬运循环：拉流 -> 推流"""
        while not self.stop_event.is_set():
            try:
                # 1. 获取原始帧
                frame = self.stream_mgr.frame_queue.get(timeout=1.0)
                frame_resized = cv2.resize(frame, (640, 360))
                # 2. 直接推流写入（不经过任何处理和画框）
                self.stream_mgr.write_frame(frame_resized)
                
            except Empty:
                continue

    def run(self):
        logger.info(f"🚀 启动纯流媒体中转服务 | 摄像头: {self.cfg.C_NAME} | ID: {self.cfg.C_ID}")
        self.stream_mgr.start()
        
        try:
            self._transfer_loop()
        except KeyboardInterrupt:
            logger.info("捕获到终止信号，准备退出...")
        finally:
            self.stop_event.set()
            self.stream_mgr.release()
            logger.info("流媒体通道已安全关闭。")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python main.py <RTSP_URL> <CAMERA_ID> <CAMERA_NAME>")
        sys.exit(1)
        
    cfg = Config(c_id=sys.argv[2], c_name=sys.argv[3], rtsp_addr=sys.argv[1])
    pipeline = PassThroughPipeline(cfg)
    pipeline.run()