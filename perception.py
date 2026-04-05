import cv2
from ultralytics import YOLO

class PerceptionSystem:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.target_classes = ['car', 'truck', 'bus', 'person', 'stop sign']
        # Lățimea medie a unei mașini în metri pentru calcul distanță
        self.KNOWN_WIDTH = 1.8 
        self.FOCAL_LENGTH = 800 # Valoare generică, se poate calibra

    def analyze(self, frame):
        results = self.model(frame, verbose=False)[0]
        detections = []
        
        for box in results.boxes:
            cls_id = int(box.cls[0])
            label = results.names[cls_id]
            conf = float(box.conf[0])
            
            if label in self.target_classes and conf > 0.4:
                coords = box.xyxy[0].cpu().numpy().astype(int)
                w_pixels = coords[2] - coords[0]
                
                # Estimare distanță: D = (W_real * Focal) / W_pixels
                distance = (self.KNOWN_WIDTH * self.FOCAL_LENGTH) / w_pixels
                
                # Calculăm poziția laterală (X relativ față de centrul imaginii)
                center_x = (coords[0] + coords[2]) / 2
                relative_x = (center_x - frame.shape[1] / 2) * (distance / self.FOCAL_LENGTH)

                detections.append({
                    "label": label,
                    "box": coords,
                    "pos_rel": (round(relative_x, 2), round(distance, 2)) # (x, z) în metri
                })
        return detections