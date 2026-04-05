import cv2
import numpy as np
import os
from ultralytics import YOLO

# Culori BGR per clasă — folosite și în main.py HUD
LABEL_COLORS = {
    "car":           (255, 150,  60),
    "truck":         ( 60, 130, 255),
    "bus":           (200,  60, 200),
    "person":        (255, 255,   0),
    "bicycle":       ( 60, 220,  60),
    "motorcycle":    (  0, 200, 255),
    "stop sign":     (  0,   0, 255),
    "traffic light": (200, 200, 200),   # gri (se suprascrie cu culoarea activă)
}

LABEL_TAGS = {
    "car":           "MASINA",
    "truck":         "CAMION",
    "bus":           "AUTOBUS",
    "person":        "PIETON",
    "bicycle":       "BICICLETA",
    "motorcycle":    "MOTOCICLETA",
    "stop sign":     "STOP",
    "traffic light": "SEMAFOR",
}

KNOWN_WIDTHS = {
    "car": 1.8, "truck": 2.5, "bus": 2.8,
    "person": 0.5, "bicycle": 0.6, "motorcycle": 0.8,
    "stop sign": 0.6, "traffic light": 0.3,
}

# COCO class IDs pentru clasele noastre
# 0=person, 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck, 9=traffic light, 11=stop sign
YOLO_CLASSES = [0, 1, 2, 3, 5, 7, 9, 11]

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "yolov8n.pt")


class PerceptionSystem:
    def __init__(self):
        self.model = YOLO(_MODEL_PATH)
        self.FOCAL_LENGTH = 800
        self.last_center_line = -250
        self.last_right_line  = 250
        self.center_history   = []
        self.right_history    = []

    # ──────────────────────────────────────────────────────────────────────────
    # LANE DETECTION
    # ──────────────────────────────────────────────────────────────────────────

    def _find_lane_x(self, warped, start_x):
        """Sliding window de jos în sus — urmărește linia chiar și la curbe."""
        h, w   = warped.shape
        n_win  = 10
        win_h  = h // n_win
        margin = 60
        min_px = 40

        cur_x = start_x
        xs    = []

        for win in range(n_win):
            y_lo = h - (win + 1) * win_h
            y_hi = h - win * win_h
            x_lo = max(0, cur_x - margin)
            x_hi = min(w, cur_x + margin)

            pix_cols = np.nonzero(warped[y_lo:y_hi, x_lo:x_hi])[1] + x_lo
            if len(pix_cols) >= min_px:
                cur_x = int(np.mean(pix_cols))
                xs.append(cur_x)

        return int(np.mean(xs)) if len(xs) >= 3 else None

    def get_lane_geometry(self, frame):
        h, w = frame.shape[:2]

        # 1. Mască combinată: HLS color + Sobel X gradient
        hls  = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        white_mask  = cv2.inRange(hls, np.array([0,  180,   0]), np.array([255, 255,  60]))
        yellow_mask = cv2.inRange(hls, np.array([15,  30, 100]), np.array([ 35, 204, 255]))

        sobelx     = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobel_mask = np.uint8(np.abs(sobelx) > 25) * 255

        combined = cv2.bitwise_or(cv2.bitwise_or(white_mask, yellow_mask), sobel_mask)

        # 2. Morfologie — umple golurile liniilor dashed
        kernel   = np.ones((5, 5), np.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

        # 3. Perspectivă bird's-eye
        src    = np.float32([[w*0.35, h*0.65], [w*0.65, h*0.65], [0, h], [w, h]])
        dst    = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        warped = cv2.warpPerspective(combined, cv2.getPerspectiveTransform(src, dst), (w, h))

        # 4. Histogramă cu prag 400
        histogram = np.sum(warped[h//2:, :], axis=0)

        l_hist = histogram[int(w*0.10):int(w*0.48)]
        r_hist = histogram[int(w*0.52):int(w*0.90)]
        l_peak = int(np.argmax(l_hist) + w*0.10) if np.max(l_hist) > 400 else None
        r_peak = int(np.argmax(r_hist) + w*0.52) if np.max(r_hist) > 400 else None

        # 5. Sliding window per linie
        left_x  = self._find_lane_x(warped, l_peak) if l_peak is not None else None
        right_x = self._find_lane_x(warped, r_peak) if r_peak is not None else None

        # 6. Update + fallback cross-lane
        LANE_WIDTH_PX = 320
        if left_x is not None:
            self.last_center_line = int(left_x - w // 2)
        if right_x is not None:
            self.last_right_line = int(right_x - w // 2)

        if left_x is not None and right_x is None:
            self.last_right_line = int((left_x + LANE_WIDTH_PX) - w // 2)
        elif right_x is not None and left_x is None:
            self.last_center_line = int((right_x - LANE_WIDTH_PX) - w // 2)

        # 7. Smoothing pe 7 frame-uri
        self.center_history.append(self.last_center_line)
        self.right_history.append(self.last_right_line)
        if len(self.center_history) > 7: self.center_history.pop(0)
        if len(self.right_history)  > 7: self.right_history.pop(0)

        return {
            "center_line": int(sum(self.center_history) / len(self.center_history)),
            "right_line":  int(sum(self.right_history)  / len(self.right_history)),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # TRAFFIC LIGHT COLOR
    # ──────────────────────────────────────────────────────────────────────────

    def get_tl_color(self, frame, box):
        x1, y1, x2, y2 = box
        h_f, w_f = frame.shape[:2]

        if (x2 - x1) > (y2 - y1):
            return "FALS (PANOU)"

        roi = frame[max(0,y1):min(h_f,y2), max(0,x1):min(w_f,x2)]
        if roi.size == 0:
            return "NECUNOSCUT"

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        r = cv2.countNonZero(cv2.bitwise_or(
            cv2.inRange(hsv, np.array([0,   50, 180]), np.array([10,  255, 255])),
            cv2.inRange(hsv, np.array([160, 50, 180]), np.array([180, 255, 255]))
        ))
        y_ = cv2.countNonZero(cv2.inRange(hsv, np.array([15, 50, 180]), np.array([35, 255, 255])))
        g  = cv2.countNonZero(cv2.inRange(hsv, np.array([35, 50, 180]), np.array([90, 255, 255])))

        if max(r, y_, g) < 5: return "INACTIV"
        if r  > y_ and r  > g: return "ROSU"
        if y_ > r  and y_ > g: return "GALBEN"
        if g  > r  and g  > y_: return "VERDE"
        return "INACTIV"

    # ──────────────────────────────────────────────────────────────────────────
    # ROAD SURFACE + GRIP CLASS  (+10p + +5p bonus)
    # ──────────────────────────────────────────────────────────────────────────

    def _estimate_road_surface(self, frame):
        """
        Analizează ROI-ul drumului (partea inferioară a frame-ului) și clasifică
        suprafața în funcție de luminozitate și variație de textură.

        Returnează:
            road_surface  : "asfalt_uscat" | "asfalt_umed" | "pietris"
            friction_mu   : coeficient de frecare (μ) — folosit în formula de frânare
            grip_class    : "A" | "B" | "C"
        """
        h, w = frame.shape[:2]
        road_roi = frame[int(h * 0.75):h, int(w * 0.2):int(w * 0.8)]
        gray_roi = cv2.cvtColor(road_roi, cv2.COLOR_BGR2GRAY)

        mean_b = float(np.mean(gray_roi))
        std_b  = float(np.std(gray_roi))

        # Asfalt umed: reflexii specular → std mare + luminozitate medie-mare
        # Pietriș: textură neuniformă → std mare + luminozitate scăzută
        # Asfalt uscat: uniform → std mică
        if std_b > 45 and mean_b > 100:
            return {"road_surface": "asfalt_umed", "friction_mu": 0.45, "grip_class": "B"}
        if std_b > 40 and mean_b < 80:
            return {"road_surface": "pietris",     "friction_mu": 0.40, "grip_class": "C"}
        return     {"road_surface": "asfalt_uscat","friction_mu": 0.70, "grip_class": "A"}

    # ──────────────────────────────────────────────────────────────────────────
    # FOG / VISIBILITY ESTIMATION  (+10p + +10p bonus)
    # ──────────────────────────────────────────────────────────────────────────

    def _estimate_visibility(self, frame):
        """
        Estimează vizibilitatea analizând contrastul zonei de orizont.
        Ceața reduce detaliile fine → contrast scăzut în banda de orizont.

        Returnează:
            visibility_m  : distanță estimată de vizibilitate (metri)
            fog_condition : "ceata_densa" | "ceata_usoara" | "vizibilitate_buna"
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h    = gray.shape[0]
        horizon = gray[int(h * 0.25):int(h * 0.50), :]
        contrast = float(np.std(horizon))

        if contrast < 18:
            return {"visibility_m": 40,  "fog_condition": "ceata_densa"}
        if contrast < 30:
            return {"visibility_m": 100, "fog_condition": "ceata_usoara"}
        return     {"visibility_m": 500, "fog_condition": "vizibilitate_buna"}

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN ANALYZE
    # ──────────────────────────────────────────────────────────────────────────

    def analyze(self, frame):
        results = self.model(
            frame, conf=0.45, imgsz=320, max_det=20,
            classes=YOLO_CLASSES, agnostic_nms=True, verbose=False
        )[0]

        detections  = []
        lanes       = self.get_lane_geometry(frame)
        road_info   = self._estimate_road_surface(frame)
        fog_info    = self._estimate_visibility(frame)

        for box in results.boxes:
            label = results.names[int(box.cls[0])]
            if label not in LABEL_TAGS:
                continue

            coords      = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = coords
            wb = max(1, x2 - x1)
            hb = max(1, y2 - y1)

            if wb * hb < 600:
                continue
            if y2 < frame.shape[0] * 0.25:
                continue

            known_w = KNOWN_WIDTHS.get(label, 1.8)
            dist_z  = (known_w * self.FOCAL_LENGTH) / wb
            rel_x   = ((x1 + x2) / 2 - frame.shape[1] / 2) * (dist_z / self.FOCAL_LENGTH)

            if dist_z < 1.5 or dist_z > 70:
                continue

            d_obj = {
                "label":   label,
                "box":     coords.tolist(),
                "pos_rel": [round(rel_x, 2), round(dist_z, 2)],
            }

            if label == "traffic light":
                tl_status = self.get_tl_color(frame, coords)
                if tl_status == "FALS (PANOU)":
                    continue
                d_obj["tl_color"] = tl_status

            detections.append(d_obj)

        return detections, lanes, road_info, fog_info
