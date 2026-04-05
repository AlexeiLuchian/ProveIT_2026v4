import cv2, time, json, os
from core.perception import PerceptionSystem, LABEL_COLORS, LABEL_TAGS
from core.logic import DrivingLogic


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
    last_save      = 0
    prev_positions = {}   # key → (rel_x, rel_z, timestamp)
    speed_history  = {}   # key → lista ultimelor N viteze (medie glisantă)

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
        detections, lanes, road_info, fog_info = eye.analyze(frame)
        decisions = brain.update(detections)

        # Estimare viteză — urmărire prin proximitate spațială, nu index
        new_prev = {}
        for o in detections:
            lbl    = o["label"]
            ox, oz = o["pos_rel"]

            # Găsim cel mai apropiat obiect din frame-ul anterior cu același label
            best_key, best_d = None, float("inf")
            for pk, (px, pz, pt) in prev_positions.items():
                if not pk.startswith(lbl + "_"):
                    continue
                d = ((ox - px) ** 2 + (oz - pz) ** 2) ** 0.5
                if d < best_d and d < 8.0:   # max 8m diferență între frame-uri
                    best_d, best_key = d, pk

            track_key = best_key if best_key else f"{lbl}_{id(o)}"
            if best_key and best_key in prev_positions:
                px, pz, pt = prev_positions[best_key]
                dt = current_time - pt
                if dt > 0:
                    raw_kmh = ((pz - oz) / dt) * 3.6   # pozitiv = se apropie
                    raw_kmh = max(-180.0, min(300.0, raw_kmh))

                    hist = speed_history.setdefault(track_key, [])
                    hist.append(raw_kmh)
                    if len(hist) > 6: hist.pop(0)
                    o["speed_kmh"] = round(max(0.0, sum(hist) / len(hist)), 1)

            new_prev[track_key] = (ox, oz, current_time)

        prev_positions = new_prev

        # ── HUD pe video ───────────────────────────────────────────────────────
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            lbl = d["label"]
            rz  = d["pos_rel"][1]

            color = LABEL_COLORS.get(lbl, (255, 255, 255))
            tag   = LABEL_TAGS.get(lbl, lbl.upper())

            if lbl == "traffic light":
                tc = d.get("tl_color", "?")
                tag = f"SEMAFOR [{tc}]"
                color = (0,0,255) if tc=="ROSU" else (0,200,0) if tc=="VERDE" else (0,200,255) if tc=="GALBEN" else (180,180,180)

            spd = f" {d['speed_kmh']}km/h" if "speed_kmh" in d else ""
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{tag} | {rz}m{spd}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        # Status decizii în colțul stâng-sus
        risk_c = (0, 0, 255) if decisions['risk_level'] == 'high' else (0, 200, 0)
        cv2.putText(frame, f"BRAKE: {decisions['brake_decision'].upper()}",
                    (20, 40),  cv2.FONT_HERSHEY_SIMPLEX, 1.2, risk_c, 3)
        cv2.putText(frame, f"SPEED: {decisions['speed_decision'].upper()}",
                    (20, 75),  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 80), 2)
        cv2.putText(frame, f"LANE:  {decisions['lane_decision'].upper()}",
                    (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 180, 255), 2)

        # Suprafată drum + vizibilitate în colțul dreapta-sus
        surf_text = f"DRUM: {road_info['road_surface'].upper()} (mu={road_info['friction_mu']})"
        fog_text  = f"VIZ: {fog_info['visibility_m']}m [{fog_info['fog_condition'].upper()}]"
        cv2.putText(frame, surf_text, (700, 40),  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)
        cv2.putText(frame, fog_text,  (700, 70),  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 230, 255), 2)

        # ── Export JSON + Log la 0.5s ──────────────────────────────────────────
        if current_time - last_save >= 0.5:
            clean_objects = []
            for o in detections:
                obj_c = {
                    "label":   o["label"],
                    "pos_rel": [float(o["pos_rel"][0]), float(o["pos_rel"][1])],
                }
                if "tl_color"  in o: obj_c["tl_color"]  = o["tl_color"]
                if "speed_kmh" in o: obj_c["speed_kmh"] = o["speed_kmh"]
                clean_objects.append(obj_c)

            data_to_send = {
                "timestamp":     round(current_time, 3),
                "decisions":     decisions,
                "lane_geometry": lanes,
                "road_info":     road_info,
                "fog_info":      fog_info,
                "objects":       clean_objects,
            }

            with open("output/data.json", "w") as f:
                json.dump(data_to_send, f, indent=4)

            bus.publish(data_to_send)

            nearest = min(detections, key=lambda x: x["pos_rel"][1], default=None)
            reason  = f"{nearest['label']}@{nearest['pos_rel'][1]}m" if nearest else "drum_liber"
            with open("output/system.log", "a") as log:
                log.write(
                    f"[{round(current_time, 2)}] "
                    f"RISK:{decisions['risk_level']} | "
                    f"BRAKE:{decisions['brake_decision']} | "
                    f"SPEED:{decisions['speed_decision']} | "
                    f"LANE:{decisions['lane_decision']} | "
                    f"REASON:{reason} | "
                    f"ROAD:{road_info['road_surface']} | "
                    f"MU:{road_info['friction_mu']} | "
                    f"GRIP:{road_info['grip_class']} | "
                    f"FOG:{fog_info['fog_condition']} | "
                    f"VIZ:{fog_info['visibility_m']}m\n"
                )

            last_save = current_time

        cv2.imshow('Magna HUD', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
