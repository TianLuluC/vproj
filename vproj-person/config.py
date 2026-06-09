import os

class Config:
    def __init__(self, c_id, c_name, rtsp_addr):
        self.HOST_IP = os.environ.get('HOST_IP')
        self.C_ID = c_id
        self.C_NAME = c_name
        self.RTSP_ADDRESS = rtsp_addr

        # --- 路径配置 ---
        self.CONF_DIR = "./conf"
        self.FONT_PATH = "./font/weiruanyahei.ttf"
        self.ENGINE_PATH = "./build/yolo11bm.engine"
        self.PLUGIN_LIBRARY = "./build/libmyplugins.so"
        
        # --- 网络与接口配置 ---
        self.API_GET_COORD = f"http://{self.HOST_IP}:8090/safevideo/message/getCoordinateByVideoId/{self.C_ID}"
        self.API_PUSH_MSG = f"http://{self.HOST_IP}:8090/safevideo/message/pushMsg"
        
        self.RTMP_HOST = self.HOST_IP
        self.RTMP_PORT = 1937
        self.RTMP_PATH = f"rtmp://{self.RTMP_HOST}:{self.RTMP_PORT}/safevideolive/pfs/{self.C_ID}"
        
        # --- 业务防误报与性能配置 ---
        self.CONFIRM_FRAMES = 3      # 连续几帧检测到违规才触发告警, 防花屏闪烁
        self.COOLDOWN_SEC = 120      # 同一事件报警冷却时间
        self.MAX_QUEUE_SIZE = 10     # 视频流缓冲队列最大长度
        
        # 确保配置目录存在
        os.makedirs(self.CONF_DIR, exist_ok=True)