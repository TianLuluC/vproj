import time
import cv2
import numpy as np
import pycuda.autoinit  # noqa: F401
import pycuda.driver as cuda
import tensorrt as trt

class YoLo11TRT:
    def __init__(self, engine_file_path, gpu_id, conf_thresh=0.5, iou_thresh=0.4):
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        
        # YOLO11 输出维度常量
        self.det_num = 6
        self.pose_num = 17 * 3
        self.seg_num = 32
        self.obb_num = 1  # YOLO11 新增的旋转框维度

        self.ctx = cuda.Device(gpu_id).make_context()
        stream = cuda.Stream()
        TRT_LOGGER = trt.Logger(trt.Logger.INFO)
        runtime = trt.Runtime(TRT_LOGGER)
        
        with open(engine_file_path, "rb") as f:
            engine = runtime.deserialize_cuda_engine(f.read())
            
        context = engine.create_execution_context()
        host_inputs, cuda_inputs, host_outputs, cuda_outputs, bindings = [], [], [], [], []
        
        for binding in engine:
            self.batch_size = engine.get_binding_shape(binding)[0]
            size = trt.volume(engine.get_binding_shape(binding)) * engine.max_batch_size
            dtype = trt.nptype(engine.get_binding_dtype(binding))
            host_mem = cuda.pagelocked_empty(size, dtype)
            cuda_mem = cuda.mem_alloc(host_mem.nbytes)
            bindings.append(int(cuda_mem))
            
            if engine.binding_is_input(binding):
                self.input_w = engine.get_binding_shape(binding)[-1]
                self.input_h = engine.get_binding_shape(binding)[-2]
                host_inputs.append(host_mem)
                cuda_inputs.append(cuda_mem)
            else:
                host_outputs.append(host_mem)
                cuda_outputs.append(cuda_mem)
                
        self.stream = stream
        self.context = context
        self.engine = engine
        self.host_inputs = host_inputs
        self.cuda_inputs = cuda_inputs
        self.host_outputs = host_outputs
        self.cuda_outputs = cuda_outputs
        self.bindings = bindings
        self.det_output_length = host_outputs[0].shape[0] // self.batch_size

    def infer(self, frame, roi_coords):
        self.ctx.push()
        input_image, image_raw, origin_h, origin_w = self._preprocess(frame)
        
        np.copyto(self.host_inputs[0], input_image.ravel())
        cuda.memcpy_htod_async(self.cuda_inputs[0], self.host_inputs[0], self.stream)
        # YOLO11 使用的是 execute_async_v2
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        cuda.memcpy_dtoh_async(self.host_outputs[0], self.cuda_outputs[0], self.stream)
        self.stream.synchronize()
        
        output = self.host_outputs[0]
        boxes, scores, classids = self._post_process(output[: self.det_output_length], origin_h, origin_w)
        
        detect_flag = False
        valid_cls_ids = []
        
        # 校验边界框是否落在 ROI 多边形内
        for j in range(len(boxes)):
            if classids[j] != 0:
                continue
            box = boxes[j]
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            box_points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            
            for i in range(roi_coords.shape[0]):
                is_inside = any(cv2.pointPolygonTest(np.array([roi_coords[i]]), pt, False) >= 0 for pt in box_points)
                if is_inside:
                    detect_flag = True
                    valid_cls_ids.append(int(classids[j]))
                    
                    label = {0: "Person", 1: "Fall", 2: "Smoke"}.get(int(classids[j]), "Unknown")
                    self._draw_box(box, image_raw, label=label)
        
        # 绘制绿色 ROI 边界区
        for i in range(roi_coords.shape[0]):
            cv2.polylines(image_raw, np.array([roi_coords[i]]), isClosed=True, color=(0, 255, 0), thickness=2)
            
        self.ctx.pop()
        return image_raw, detect_flag, np.array(valid_cls_ids)

    def _draw_box(self, x, img, color=[0, 0, 255], label=None):
        c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
        cv2.rectangle(img, c1, c2, color, thickness=2, lineType=cv2.LINE_AA)
        if label:
            t_size = cv2.getTextSize(label, 0, fontScale=0.5, thickness=1)[0]
            c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
            cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)
            cv2.putText(img, label, (c1[0], c1[1] - 2), 0, 0.5, [225, 255, 255], thickness=1, lineType=cv2.LINE_AA)

    def _preprocess(self, raw_bgr_image):
        """带有 LetterBox 填充的预处理 (YOLO11标准)"""
        image_raw = raw_bgr_image
        h, w, _ = image_raw.shape
        image = cv2.cvtColor(image_raw, cv2.COLOR_BGR2RGB)
        
        r_w = self.input_w / w
        r_h = self.input_h / h
        if r_h > r_w:
            tw = self.input_w
            th = int(r_w * h)
            tx1 = tx2 = 0
            ty1 = int((self.input_h - th) / 2)
            ty2 = self.input_h - th - ty1
        else:
            tw = int(r_h * w)
            th = self.input_h
            tx1 = int((self.input_w - tw) / 2)
            tx2 = self.input_w - tw - tx1
            ty1 = ty2 = 0
            
        image = cv2.resize(image, (tw, th))
        image = cv2.copyMakeBorder(image, ty1, ty2, tx1, tx2, cv2.BORDER_CONSTANT, None, (128, 128, 128))
        image = image.astype(np.float32) / 255.0
        image = np.transpose(image, [2, 0, 1])
        return np.ascontiguousarray(image), image_raw, h, w

    def _xywh2xyxy(self, origin_h, origin_w, x):
        """反演坐标到原始图像尺度"""
        y = np.zeros_like(x)
        r_w = self.input_w / origin_w
        r_h = self.input_h / origin_h
        if r_h > r_w:
            y[:, 0] = x[:, 0]
            y[:, 2] = x[:, 2]
            y[:, 1] = x[:, 1] - (self.input_h - r_w * origin_h) / 2
            y[:, 3] = x[:, 3] - (self.input_h - r_w * origin_h) / 2
            y /= r_w
        else:
            y[:, 0] = x[:, 0] - (self.input_w - r_h * origin_w) / 2
            y[:, 2] = x[:, 2] - (self.input_w - r_h * origin_w) / 2
            y[:, 1] = x[:, 1]
            y[:, 3] = x[:, 3]
            y /= r_h
        return y

    def bbox_iou(self, box1, box2, x1y1x2y2=True):
        if not x1y1x2y2:
            b1_x1, b1_x2 = box1[:, 0] - box1[:, 2] / 2, box1[:, 0] + box1[:, 2] / 2
            b1_y1, b1_y2 = box1[:, 1] - box1[:, 3] / 2, box1[:, 1] + box1[:, 3] / 2
            b2_x1, b2_x2 = box2[:, 0] - box2[:, 2] / 2, box2[:, 0] + box2[:, 2] / 2
            b2_y1, b2_y2 = box2[:, 1] - box2[:, 3] / 2, box2[:, 1] + box2[:, 3] / 2
        else:
            b1_x1, b1_y1, b1_x2, b1_y2 = box1[:, 0], box1[:, 1], box1[:, 2], box1[:, 3]
            b2_x1, b2_y1, b2_x2, b2_y2 = box2[:, 0], box2[:, 1], box2[:, 2], box2[:, 3]

        inter_rect_x1 = np.maximum(b1_x1, b2_x1)
        inter_rect_y1 = np.maximum(b1_y1, b2_y1)
        inter_rect_x2 = np.minimum(b1_x2, b2_x2)
        inter_rect_y2 = np.minimum(b1_y2, b2_y2)
        
        inter_area = (np.clip(inter_rect_x2 - inter_rect_x1 + 1, 0, None) * np.clip(inter_rect_y2 - inter_rect_y1 + 1, 0, None))
        b1_area = (b1_x2 - b1_x1 + 1) * (b1_y2 - b1_y1 + 1)
        b2_area = (b2_x2 - b2_x1 + 1) * (b2_y2 - b2_y1 + 1)

        iou = inter_area / (b1_area + b2_area - inter_area + 1e-16)
        return iou

    def non_max_suppression(self, prediction, origin_h, origin_w, conf_thres, nms_thres):
        boxes = prediction[prediction[:, 4] >= conf_thres]
        if len(boxes) == 0: return np.array([])
        
        boxes[:, :4] = self._xywh2xyxy(origin_h, origin_w, boxes[:, :4])
        boxes[:, 0] = np.clip(boxes[:, 0], 0, origin_w - 1)
        boxes[:, 2] = np.clip(boxes[:, 2], 0, origin_w - 1)
        boxes[:, 1] = np.clip(boxes[:, 1], 0, origin_h - 1)
        boxes[:, 3] = np.clip(boxes[:, 3], 0, origin_h - 1)
        
        confs = boxes[:, 4]
        boxes = boxes[np.argsort(-confs)]
        keep_boxes = []
        
        while boxes.shape[0]:
            large_overlap = self.bbox_iou(np.expand_dims(boxes[0, :4], 0), boxes[:, :4]) > nms_thres
            label_match = boxes[0, -1] == boxes[:, -1]
            invalid = large_overlap & label_match
            keep_boxes += [boxes[0]]
            boxes = boxes[~invalid]
            
        return np.stack(keep_boxes, 0) if len(keep_boxes) else np.array([])

    def _post_process(self, output, origin_h, origin_w):
        # 包含了新增的 OBB_NUM
        num_values_per_detection = self.det_num + self.seg_num + self.pose_num + self.obb_num
        num = int(output[0])
        pred = np.reshape(output[1:], (-1, num_values_per_detection))[:num, :]
        
        boxes = self.non_max_suppression(pred, origin_h, origin_w, conf_thres=self.conf_thresh, nms_thres=self.iou_thresh)
        
        result_boxes = boxes[:, :4] if len(boxes) else np.array([])
        result_scores = boxes[:, 4] if len(boxes) else np.array([])
        result_classid = boxes[:, 5] if len(boxes) else np.array([])
        
        return result_boxes, result_scores, result_classid

    def destroy(self):
        self.ctx.pop()