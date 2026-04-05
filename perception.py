import cv2
import numpy as np
from ultralytics import YOLO

class PerceptionSystem:
    def __init__(self):
        # Folosim modelul Nano pentru viteză
        self.model = YOLO('yolov8n.pt')
        self.FOCAL_LENGTH = 800
        self.KNOWN_WIDTH = 1.8
        
        # Memoria benzilor pentru a stabiliza randarea
        self.last_center_line = -250
        self.last_right_line = 250
        
        self.target_classes = ['car', 'truck', 'bus', 'person', 'stop sign', 'traffic light']

    def get_center_line(self, frame):
        """Găsește axul drumului (stânga) și linia benzii (dreapta)."""
        h, w = frame.shape[:2]
        
        hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        white_mask = cv2.inRange(hls, np.array([0, 200, 0]), np.array([255, 255, 255]))
        yellow_mask = cv2.inRange(hls, np.array([15, 30, 115]), np.array([35, 204, 255]))
        mask = cv2.bitwise_or(white_mask, yellow_mask)
        
        src = np.float32([[w*0.35, h*0.65], [w*0.65, h*0.65], [0, h], [w, h]])
        dst = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        matrix = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(mask, matrix, (w, h))
        
        histogram = np.sum(warped[h//2:, :], axis=0)
        
        # 1. Căutare Stânga (Linia de Contrasens / Centru)
        left_search = histogram[int(w * 0.2):int(w * 0.5)]
        if np.max(left_search) > 800: 
            peak_x_left = int(np.argmax(left_search)) + int(w * 0.2)
            self.last_center_line = int(peak_x_left - (w // 2))

        # 2. Căutare Dreapta (Linia de pe sensul tău)
        right_search = histogram[int(w * 0.5):int(w * 0.8)]
        if np.max(right_search) > 800:
            peak_x_right = int(np.argmax(right_search)) + int(w * 0.5)
            self.last_right_line = int(peak_x_right - (w // 2))

        # ATENȚIE: Folosim int() pentru a evita eroarea JSON cu numpy.int64
        return {
            "center_line": int(self.last_center_line),
            "right_line": int(self.last_right_line)
        }

    def get_tl_color(self, frame, box):
        """Analizează semaforul, filtrând panourile publicitare."""
        x1, y1, x2, y2 = box
        h_frame, w_frame = frame.shape[:2]
        
        box_width = x2 - x1
        box_height = y2 - y1
        
        # Dacă e mai lat decât înalt, este panou, nu semafor
        if box_width > box_height: return "FALS (PANOU)"

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_frame, x2), min(h_frame, y2)
        roi = frame[y1:y2, x1:x2]
        
        if roi.size == 0: return "NECUNOSCUT"

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Filtru de luminozitate (căutăm doar LED-uri aprinse, nu vopsea mată)
        mask_red = cv2.bitwise_or(
            cv2.inRange(hsv, np.array([0, 50, 180]), np.array([10, 255, 255])),
            cv2.inRange(hsv, np.array([160, 50, 180]), np.array([180, 255, 255]))
        )
        mask_yellow = cv2.inRange(hsv, np.array([15, 50, 180]), np.array([35, 255, 255]))
        mask_green = cv2.inRange(hsv, np.array([35, 50, 180]), np.array([90, 255, 255]))

        r = cv2.countNonZero(mask_red)
        y = cv2.countNonZero(mask_yellow)
        g = cv2.countNonZero(mask_green)

        if max(r, y, g) < 5: return "INACTIV"

        if r > y and r > g: return "ROSU"
        elif y > r and y > g: return "GALBEN"
        elif g > r and g > y: return "VERDE"
        
        return "INACTIV"

    def detect_european_signs(self, frame):
        """Detector personalizat pentru Rombul de Prioritate și Cercul de Interzis."""
        h, w = frame.shape[:2]
        # Scanăm doar partea de sus (unde sunt semnele)
        roi_h = int(h * 0.4)
        roi = frame[0:roi_h, 0:w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        extra_signs = []
        sign_width_meters = 0.6 

        # 1. Romb Galben
        mask_yellow = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([35, 255, 255]))
        contours_y, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours_y:
            area = cv2.contourArea(cnt)
            if 400 < area < 4000:
                approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
                if len(approx) == 4: 
                    x, y, w_box, h_box = cv2.boundingRect(approx)
                    if 0.8 < w_box/h_box < 1.2: # E aproximativ pătrat
                        dist_z = (sign_width_meters * self.FOCAL_LENGTH) / w_box
                        rel_x = ((x + w_box/2) - (w / 2)) * (dist_z / self.FOCAL_LENGTH)
                        extra_signs.append({
                            "label": "priority_sign",
                            "box": [x, y, x+w_box, y+h_box],
                            "pos_rel": [round(rel_x, 2), round(dist_z, 2)]
                        })

        # 2. Cerc Roșu
        mask_red = cv2.bitwise_or(
            cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
            cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        )
        contours_r, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours_r:
            area = cv2.contourArea(cnt)
            if 400 < area < 4000:
                approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)
                if len(approx) > 6: 
                    x, y, w_box, h_box = cv2.boundingRect(approx)
                    if 0.8 < w_box/h_box < 1.2:
                        dist_z = (sign_width_meters * self.FOCAL_LENGTH) / w_box
                        rel_x = ((x + w_box/2) - (w / 2)) * (dist_z / self.FOCAL_LENGTH)
                        extra_signs.append({
                            "label": "restriction_sign",
                            "box": [x, y, x+w_box, y+h_box],
                            "pos_rel": [round(rel_x, 2), round(dist_z, 2)]
                        })

        return extra_signs

    def analyze(self, frame):
        # conf=0.4 oprește lag-ul masiv al NMS
        results = self.model(frame, conf=0.4, imgsz=640, verbose=False)[0]
        detections = []
        
        lane_geometry = self.get_center_line(frame)
        
        # Procesăm obiectele YOLO
        for box in results.boxes:
            cls = int(box.cls[0])
            label = results.names[cls]
            
            if label in self.target_classes:
                coords = box.xyxy[0].cpu().numpy().astype(int)
                w_pixels = coords[2] - coords[0]
                if w_pixels == 0: continue
                
                dist_z = (self.KNOWN_WIDTH * self.FOCAL_LENGTH) / w_pixels
                obj_center_x = (coords[0] + coords[2]) / 2
                rel_x = (obj_center_x - (frame.shape[1] / 2)) * (dist_z / self.FOCAL_LENGTH)
                
                obj_data = {
                    "label": label, 
                    "box": coords.tolist(), 
                    "pos_rel": [round(rel_x, 2), round(dist_z, 2)]
                }
                
                if label == 'traffic light':
                    tl_status = self.get_tl_color(frame, coords)
                    if tl_status == "FALS (PANOU)": continue 
                    obj_data["tl_color"] = tl_status
                    
                detections.append(obj_data)
        
        # Lipim și semnele noastre personalizate europene
        euro_signs = self.detect_european_signs(frame)
        detections.extend(euro_signs)
        
        return detections, lane_geometry