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
        self.center_history = []
        self.right_history = []
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

        # Linia stângă (contrasens)
        l_search = histogram[int(w*0.15):int(w*0.5)]
        if len(l_search) > 0 and np.max(l_search) > 800:
            self.last_center_line = int(np.argmax(l_search) + w*0.15 - (w//2))

        # Linia dreaptă (banda curentă)
        r_search = histogram[int(w*0.5):int(w*0.85)]
        if len(r_search) > 0 and np.max(r_search) > 800:
            self.last_right_line = int(np.argmax(r_search) + w*0.5 - (w//2))

        # Smoothing — medie pe ultimele 5 valori
        self.center_history.append(self.last_center_line)
        self.right_history.append(self.last_right_line)
        if len(self.center_history) > 5: self.center_history.pop(0)
        if len(self.right_history) > 5:  self.right_history.pop(0)

        return {
            "center_line": int(sum(self.center_history) / len(self.center_history)),
            "right_line":  int(sum(self.right_history)  / len(self.right_history))
        }

    def get_tl_color(self, frame, box):
        x1, y1, x2, y2 = box
        h_frame, w_frame = frame.shape[:2]

        # Filtrare false positive: semafoarele sunt înalte, nu late
        if (x2 - x1) > (y2 - y1):
            return "FALS (PANOU)"

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_frame, x2), min(h_frame, y2)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return "NECUNOSCUT"

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask_red = cv2.bitwise_or(
            cv2.inRange(hsv, np.array([0,   50, 180]), np.array([10,  255, 255])),
            cv2.inRange(hsv, np.array([160, 50, 180]), np.array([180, 255, 255]))
        )
        mask_yellow = cv2.inRange(hsv, np.array([15, 50, 180]), np.array([35, 255, 255]))
        mask_green  = cv2.inRange(hsv, np.array([35, 50, 180]), np.array([90, 255, 255]))

        r = cv2.countNonZero(mask_red)
        y = cv2.countNonZero(mask_yellow)
        g = cv2.countNonZero(mask_green)

        if max(r, y, g) < 5:
            return "INACTIV"
        if r > y and r > g:   return "ROSU"
        if y > r and y > g:   return "GALBEN"
        if g > r and g > y:   return "VERDE"
        return "INACTIV"

    def analyze(self, frame):
        # classes: 0=person, 2=car, 5=bus, 7=truck, 9=traffic light, 11=stop sign (COCO IDs)
        results = self.model(
            frame, conf=0.45, imgsz=416, max_det=30,
            classes=[0, 2, 5, 7, 9, 11], verbose=False
        )[0]
        detections = []
        lanes = self.get_lane_geometry(frame)

        for box in results.boxes:
            label = results.names[int(box.cls[0])]
            if label not in self.target_classes:
                continue

            coords = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = coords
            wb = max(1, x2 - x1)
            hb = max(1, y2 - y1)

            # Filtru dimensiune minimă — bounding box-uri prea mici sunt zgomot
            if wb * hb < 600:
                continue

            # Filtru poziție verticală — obiectele sub linia orizontului sunt pe carosabil
            # Cele din treimea superioară a imaginii sunt cer/clădiri, nu trafic relevant
            frame_h = frame.shape[0]
            if y2 < frame_h * 0.25:
                continue

            # Lățimi reale per categorie — esențial pentru distanță corectă
            known_w = {"car": 1.8, "truck": 2.5, "bus": 2.8,
                       "person": 0.5, "stop sign": 0.6, "traffic light": 0.3}.get(label, 1.8)
            dist_z = (known_w * self.FOCAL_LENGTH) / wb
            rel_x  = ((x1 + x2) / 2 - frame.shape[1] / 2) * (dist_z / self.FOCAL_LENGTH)

            # Filtru distanță: sub 1.5m e imposibil (obiect suprapus pe capotă)
            # Peste 70m e prea departe pentru decizii relevante
            if dist_z < 1.5 or dist_z > 70:
                continue

            d_obj = {
                "label": label,
                "box": coords.tolist(),
                "pos_rel": [round(rel_x, 2), round(dist_z, 2)]
            }

            if label == 'traffic light':
                tl_status = self.get_tl_color(frame, coords)
                if tl_status == "FALS (PANOU)":
                    continue
                d_obj["tl_color"] = tl_status

            detections.append(d_obj)

        return detections, lanes
