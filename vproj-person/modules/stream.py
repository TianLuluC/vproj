import time
import cv2
import numpy as np
import threading
import subprocess as sp
import ffmpeg
import logging
from queue import Queue

logger = logging.getLogger("StreamManager")

class StreamManager:
    def __init__(self, config, stop_event):
        self.cfg = config
        self.stop_event = stop_event
        self.frame_queue = Queue(maxsize=self.cfg.MAX_QUEUE_SIZE)
        self.ffmpeg_reader = None
        self.ffmpeg_writer = None
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        
        self._push_cmd = [
            'ffmpeg', '-re', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
            '-pixel_format', 'bgr24', '-video_size', '640x360', '-i', '-',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
            '-b:v', '800k', '-bufsize', '2M', '-rtbufsize', '4M',
            '-pix_fmt', 'yuv420p', '-flvflags', 'no_duration_filesize', '-f', 'flv', self.cfg.RTMP_PATH
        ]

    def start(self):
        self._init_writer()
        self.read_thread.start()

    def _init_reader(self):
        if self.ffmpeg_reader:
            try:
                self.ffmpeg_reader.kill()
                self.ffmpeg_reader.wait(timeout=1)
            except Exception:
                pass
        try:
            self.ffmpeg_reader = (
                ffmpeg.input(self.cfg.RTSP_ADDRESS, 
                             rtsp_transport='tcp', 
                             rtbufsize='10M',
                             stimeout='5000000') 
                .output('pipe:', format='rawvideo', pix_fmt='bgr24', vf="scale=640:360", loglevel='quiet')
                .run_async(pipe_stdout=True)
            )
            logger.info("RTSP 拉流引擎已启动/重启")
        except Exception as e:
            logger.error(f"RTSP 初始化失败: {e}")

    def _init_writer(self):
        if self.ffmpeg_writer:
            try:
                self.ffmpeg_writer.kill()
                self.ffmpeg_writer.wait(timeout=1)
            except Exception:
                pass
        try:
            self.ffmpeg_writer = sp.Popen(self._push_cmd, shell=False, stdin=sp.PIPE, stderr=sp.DEVNULL)
            logger.info("RTMP 推流引擎已启动/重启")
        except Exception as e:
            logger.error(f"RTMP 推流初始化失败: {e}")

    def _read_loop(self):
        self._init_reader()
        frame_bytes_size = 640 * 360 * 3
        while not self.stop_event.is_set():
            if not self.ffmpeg_reader or self.ffmpeg_reader.poll() is not None:
                logger.warning("RTSP 流已断开或 FFmpeg 崩溃，尝试重连...")
                time.sleep(3)
                self._init_reader()
                continue
                
            try:
                in_bytes = self.ffmpeg_reader.stdout.read(frame_bytes_size)
                if not in_bytes or len(in_bytes) != frame_bytes_size:
                    raise EOFError("视频流空数据或数据不完整")
                    
                frame = np.frombuffer(in_bytes, dtype=np.uint8).reshape((360, 640, 3))
                frame_resized = cv2.resize(frame, (640, 640)) # YOLO 尺寸
                
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                    
                self.frame_queue.put(frame_resized)
                time.sleep(0.01)
            except Exception as e:
                logger.warning(f"视频流读取异常，准备重启拉流: {e}")
                self._init_reader()
                time.sleep(1)

    def write_frame(self, frame_bgr):
        """写入流媒体管道"""
        if self.stop_event.is_set(): return
        if not self.ffmpeg_writer or self.ffmpeg_writer.poll() is not None:
            self._init_writer()
            
        try:
            self.ffmpeg_writer.stdin.write(frame_bgr.tobytes())
            self.ffmpeg_writer.stdin.flush()
        except Exception as e:
            logger.error(f"推流管道破裂，尝试重建: {e}")
            self._init_writer()

    def release(self):
        if self.ffmpeg_reader: 
            try: self.ffmpeg_reader.kill() 
            except: pass
        if self.ffmpeg_writer: 
            try: self.ffmpeg_writer.kill()
            except: pass