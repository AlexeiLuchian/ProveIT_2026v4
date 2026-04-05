import cv2, time, json, os
from perception import PerceptionSystem
from logic import DrivingLogic


class DataBus:
    """Observer pattern: perception/logic publică date, renderer-ele se pot abona."""
    def __init__(self):
        self._observers = []

    def subscribe(self, fn):
        self._observers.append(fn)

    def publish(self, data):
        for fn in self._observers:
            fn(data)


bus = DataBus()


def main():
    cap = cv2.VideoCapture("video_test.mp4")
    eye, brain = PerceptionSystem(), DrivingLogic()
    last_save = 0
    prev_positions = {}  # pentru estimarea vitezei obiectelor

    if not os.path.exists("output"):
        os.makedirs("output")

    cv2.namedWindow('Magna HUD', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Magna HUD', 1280, 720)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (1280, 720))

        current_time = time.time()
        detections, lanes = eye.analyze(frame)
        decisions = brain.update(detections)

        # Estimare viteză obiecte (din variația distanței între frame-uri)
        for i, o in enumerate(detections):
            key = f"{o['label']}_{i}"
            if key in prev_positions:
                prev_z, prev_t = prev_positions[key]
                dt = current_time - prev_t
                if dt > 0:
                    dz = prev_z - o["pos_rel"][1]  # pozitiv = se apropie
                    o["speed_kmh"] = round((dz / dt) * 3.6, 1)
            prev_positions[key] = (o["pos_rel"][1], current_time)

        # HUD pe video
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            lbl, rz = d["label"], d["pos_rel"][1]

            if lbl in ['car', 'bus', 'truck']:
                tag, color = "MASINA", (255, 150, 100)
            elif lbl == 'person':
                tag, color = "OM", (0, 255, 255)
            elif lbl == 'stop sign':
                tag, color = "STOP", (0, 0, 255)
            elif lbl == 'traffic light':
                tc = d.get("tl_color", "?")
                tag = f"SEMAFOR [{tc}]"
                color = (0,0,255) if tc=="ROSU" else (0,255,0) if tc=="VERDE" else (0,255,255) if tc=="GALBEN" else (200,200,200)
            else:
                tag, color = lbl.upper(), (255, 255, 255)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            spd = f" {d['speed_kmh']}km/h" if "speed_kmh" in d else ""
            cv2.putText(frame, f"{tag} | {rz}m{spd}", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        # Status sistem în HUD
        status_c = (0, 0, 255) if decisions['risk_level'] == 'high' else (0, 255, 0)
        cv2.putText(frame, f"BRAKE: {decisions['brake_decision'].upper()}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_c, 3)
        cv2.putText(frame, f"SPEED: {decisions['speed_decision'].upper()}", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 80), 2)
        cv2.putText(frame, f"LANE:  {decisions['lane_decision'].upper()}",  (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 180, 255), 2)

        # Export JSON + Log la 0.5s
        if current_time - last_save >= 0.5:
            clean_objects = []
            for o in detections:
                obj_c = {"label": o["label"], "pos_rel": [float(o["pos_rel"][0]), float(o["pos_rel"][1])]}
                if "tl_color" in o:   obj_c["tl_color"]   = o["tl_color"]
                if "speed_kmh" in o:  obj_c["speed_kmh"]  = o["speed_kmh"]
                clean_objects.append(obj_c)

            data_to_send = {
                "timestamp": round(current_time, 3),
                "decisions": decisions,
                "lane_geometry": lanes,
                "objects": clean_objects
            }

            with open("output/data.json", "w") as f:
                json.dump(data_to_send, f, indent=4)

            bus.publish(data_to_send)

            nearest = min(detections, key=lambda x: x["pos_rel"][1], default=None)
            reason = f"{nearest['label']}@{nearest['pos_rel'][1]}m" if nearest else "drum_liber"
            with open("output/system.log", "a") as log:
                log.write(
                    f"[{round(current_time, 2)}] "
                    f"RISK:{decisions['risk_level']} | "
                    f"BRAKE:{decisions['brake_decision']} | "
                    f"SPEED:{decisions['speed_decision']} | "
                    f"LANE:{decisions['lane_decision']} | "
                    f"REASON:{reason}\n"
                )

            last_save = current_time

        cv2.imshow('Magna HUD', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
