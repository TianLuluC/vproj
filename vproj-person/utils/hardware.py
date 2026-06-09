import pynvml
import logging

logger = logging.getLogger("Hardware")

def find_available_gpu():
    """查找显存剩余量大于10%的GPU"""
    pynvml.nvmlInit()
    gpu_count = pynvml.nvmlDeviceGetCount()
    logger.info(f"Total GPUs detected: {gpu_count}")
    
    for device_id in range(gpu_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        usage_percent = (mem_info.used / mem_info.total) * 100
        remaining_percent = 100 - usage_percent
        logger.info(f"GPU {device_id} remaining memory: {remaining_percent:.2f}%")
        if remaining_percent > 10:
            return device_id
    
    return -1 # 表示无可用显卡