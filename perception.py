import cv2
import numpy as np
from ultralytics import YOLO

class PerceptionSystem:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.FOCAL_LENGTH = 800
        self.KNOWN_WIDTH = 1.8
        
        # Memoria benzilor: previne "dispariția" benzii dacă nu e vizibilă un cadru
        self.last_left_x = -300
        self.last_right_x = 300

    def get_lane_geometry(self, frame):
        h, w = frame.shape[:2]
        
        # 1. Izolăm culorile Alb și Galben (Spațiul HLS este imun la umbre)
        hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        white_mask = cv2.inRange(hls, np.array([0, 200, 0]), np.array([255, 255, 255]))
        yellow_mask = cv2.inRange(hls, np.array([15, 30, 115]), np.array([35, 204, 255]))
        mask = cv2.bitwise_or(white_mask, yellow_mask)
        
        # 2. Transformare Bird's Eye View (Decupăm drumul și îl privim de sus)
        src = np.float32([[w*0.45, h*0.65], [w*0.55, h*0.65], [w*0.1, h], [w*0.9, h]])
        dst = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        matrix = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(mask, matrix, (w, h))
        
        # 3. Histogramă (Găsim pe ce axă X se concentrează pixelii de marcaj)
        histogram = np.sum(warped[h//2:, :], axis=0)
        midpoint = int(histogram.shape[0] // 2)
        
        # Vârfurile histogramei reprezintă baza liniilor
        left_peak = np.argmax(histogram[:midpoint])
        right_peak = np.argmax(histogram[midpoint:]) + midpoint
        
        # Actualizăm memoria doar dacă găsim linii clare (evităm zgomotul)
        if np.max(histogram[:midpoint]) > 1000: 
            self.last_left_x = int(left_peak) - (w // 2) # Offset față de centru
        if np.max(histogram[midpoint:]) > 1000: 
            self.last_right_x = int(right_peak) - (w // 2)

        # Returnăm coordonatele benzilor, relative la centrul mașinii
        return {
            "left_lane": self.last_left_x,
            "right_lane": self.last_right_x,
            "lane_width": self.last_right_x - self.last_left_x
        }

    def analyze(self, frame):
        results = self.model(frame, verbose=False)[0]
        detections = []
        
        # Obținem geometria drumului
        lane_geometry = self.get_lane_geometry(frame)
        
        for box in results.boxes:
            if float(box.conf[0]) > 0.4:
                cls = int(box.cls[0])
                label = results.names[cls]
                if label in ['car', 'truck', 'bus', 'person', 'stop sign']:
                    coords = box.xyxy[0].cpu().numpy().astype(int)
                    w_pixels = coords[2] - coords[0]
                    if w_pixels == 0: continue
                    
                    dist_z = (self.KNOWN_WIDTH * self.FOCAL_LENGTH) / w_pixels
                    obj_center_x = (coords[0] + coords[2]) / 2
                    rel_x = (obj_center_x - (frame.shape[1] / 2)) * (dist_z / self.FOCAL_LENGTH)
                    
                    detections.append({
                        "label": label, 
                        "box": coords.tolist(), 
                        "pos_rel": [round(rel_x, 2), round(dist_z, 2)]
                    })
        
        return detections, lane_geometry