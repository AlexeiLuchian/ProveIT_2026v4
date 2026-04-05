import cv2
import numpy as np
from ultralytics import YOLO

class PerceptionSystem:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.FOCAL_LENGTH = 800
        self.KNOWN_WIDTH = 1.8
        self.last_center_line = -250
        self.last_right_line = 250
        self.target_classes = ['car', 'truck', 'bus', 'person', 'stop sign', 'traffic light']

    def get_lane_geometry(self, frame):
        h, w = frame.shape[:2]
        hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        mask = cv2.bitwise_or(
            cv2.inRange(hls, np.array([0, 200, 0]), np.array([255, 255, 255])),
            cv2.inRange(hls, np.array([15, 30, 115]), np.array([35, 204, 255]))
        )
        
        src = np.float32([[w*0.35, h*0.65], [w*0.65, h*0.65], [0, h], [w, h]])
        dst = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        warped = cv2.warpPerspective(mask, cv2.getPerspectiveTransform(src, dst), (w, h))
        histogram = np.sum(warped[h//2:, :], axis=0)
        
        # Linia Stânga
        l_search = histogram[int(w*0.15):int(w*0.5)]
        if len(l_search) > 0 and np.max(l_search) > 800:
            self.last_center_line = int(np.argmax(l_search) + w*0.15 - (w//2))
            
        # Linia Dreapta
        r_search = histogram[int(w*0.5):int(w*0.85)]
        if len(r_search) > 0 and np.max(r_search) > 800:
            self.last_right_line = int(np.argmax(r_search) + w*0.5 - (w//2))

        return {"center_line": int(self.last_center_line), "right_line": int(self.last_right_line)}

    def analyze(self, frame):
        results = self.model(frame, conf=0.28, imgsz=640, verbose=False)[0]
        detections = []
        lanes = self.get_lane_geometry(frame)
        
        for box in results.boxes:
            label = results.names[int(box.cls[0])]
            if label in self.target_classes:
                coords = box.xyxy[0].cpu().numpy().astype(int)
                wb = max(1, coords[2] - coords[0])
                dist_z = (self.KNOWN_WIDTH * self.FOCAL_LENGTH) / wb
                rel_x = ((coords[0]+coords[2])/2 - frame.shape[1]/2) * (dist_z / self.FOCAL_LENGTH)
                
                if dist_z > 70: continue
                
                d_obj = {"label": label, "box": coords.tolist(), "pos_rel": [round(rel_x, 2), round(dist_z, 2)]}
                if label == 'traffic light': d_obj["tl_color"] = "VERDE" 
                detections.append(d_obj)
        return detections, lanes