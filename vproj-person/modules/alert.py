import time
import base64
import requests
import datetime
import threading
import logging
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image

logger = logging.getLogger("AlertManager")

class AlertManager:
    def __init__(self, config):
        self.config = config
        self.alert_counter = 0
        self.last_alert_time = 0.0
        try:
            self.font = ImageFont.truetype(self.config.FONT_PATH, 14)
        except Exception as e:
            logger.error(f"字体加载失败，请检查路径: {e}")
            self.font = ImageFont.load_default()

    def process(self, frame_pil, draw, detect_flag, cls_ids):
        """处理每帧画面，叠加 OSD 字体并管理报警状态机"""
        current_time = time.time()
        
        # 基础运行提示
        draw.text((15, 40), "未佩戴安全帽、摔倒、抽烟正常监测中", (50, 205, 50), font=self.font)
        
        if detect_flag:
            self.alert_counter += 1
            msg_desc = self._get_alert_desc(cls_ids)
            draw.text((15, 80), f"！！！{msg_desc}，请注意查看", (60, 20, 220), font=self.font)
            
            # 满足连续N帧确信，且经过冷却时间
            if self.alert_counter >= self.config.CONFIRM_FRAMES:
                if current_time - self.last_alert_time >= self.config.COOLDOWN_SEC:
                    self._push_to_cloud(frame_pil, msg_desc)
                    self.last_alert_time = current_time
        else:
            # 平滑递减误报计数器
            self.alert_counter = max(0, self.alert_counter - 1)
            draw.text((15, 80), "未发现人员违规行为", (50, 205, 50), font=self.font)
            
        return frame_pil

    def _get_alert_desc(self, cls_ids):
        ids = set(cls_ids)
        if 0 in ids: return "疑似发现未佩戴安全帽!!!"
       

    def _push_to_cloud(self, frame_pil, msg_desc):
        def _task():
            try:
                frame_cv = np.array(frame_pil)
                _, img_bytes = cv2.imencode('.jpg', frame_cv)
                msg = {
                    "msgId": self.config.C_ID,
                    "msgType": "person",
                    "msgDesc": msg_desc,
                    "cameraLocation": self.config.C_NAME,
                    "content": base64.b64encode(img_bytes).decode('utf-8'),
                    "alarmTime": datetime.datetime.now().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
                }
                requests.post(self.config.API_PUSH_MSG, json=msg, timeout=5)
                logger.warning(f"已向云端触发告警: {msg_desc}")
            except Exception as e:
                logger.error(f"告警推送失败: {e}")
                
        threading.Thread(target=_task, daemon=True).start()