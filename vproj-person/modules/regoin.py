import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

import json
import requests
import numpy as np
import logging
from config import Config

logger = logging.getLogger("RegionManager")

class RegionManager:
    def __init__(self, config):
        self.config = config
        self.json_path = os.path.join(self.config.CONF_DIR, f"data_{self.config.C_ID}.json")

    def fetch_and_save(self):
        """从远端接口拉取坐标并保存本地"""
        try:
            ret = requests.get(url=self.config.API_GET_COORD, timeout=10)
            if ret.status_code == 200:
                res = ret.json()
                data = res["obj"]["coordinateDTOS"][0]["area"]
                with open(self.json_path, 'w') as f:
                    json.dump(data, f)
                logger.info(f"ROI 坐标数据已成功拉取并保存至 {self.json_path}")
        except Exception as e:
            logger.error(f"获取 ROI 坐标失败，将使用全屏默认坐标: {e}")

    def load_coordinates(self):
        """加载本地坐标数据"""
        if not os.path.exists(self.json_path):
            self.fetch_and_save()

        try:
            with open(self.json_path, 'r') as f:
                data_list = json.load(f)
            array_from_json = np.array(data_list)
            
            # 校验点数是否足够构成多边形 (至少3个点)
            counts = [len(array_from_json[i]) for i in range(array_from_json.shape[0])]
            if all(count < 3 for count in counts):
                raise ValueError("坐标点不足 3 个")
            return array_from_json
        except Exception as e:
            logger.warning(f"解析 ROI 失败，采用默认全屏数据: {e}")
            return np.array([[[0, 0], [640, 0], [640, 640], [0, 640]]])


if __name__ == "__main__":
     
    cfg = Config(c_id=sys.argv[1], c_name=None, rtsp_addr=None)
    RegionManager(cfg).fetch_and_save()