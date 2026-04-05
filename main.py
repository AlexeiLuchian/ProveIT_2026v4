import cv2
import time
import json
import os
from perception import PerceptionSystem
from logic import DrivingLogic

def main():
    video_path = "video_test.mp4"
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Eroare: Nu s-a putut deschide videoclipul {video_path}")
        return

    eye = PerceptionSystem()
    brain = DrivingLogic()
    
    last_save_time = 0
    output_dir = "output"
    
    if not os.path.exists(output_dir): 
        os.makedirs(output_dir)

    cv2.namedWindow('Magna AI - Heads Up Display', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Magna AI - Heads Up Display', 1280, 720)

    print("Sistem AI pornit. Procesare video în curs...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.resize(frame, (1280, 720))

        # 1. PERCEPȚIE & LOGICĂ
        detections, lanes = eye.analyze(frame)
        decisions = brain.update(detections)

        # 2. VIZUALIZARE HUD PE VIDEO
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            lbl_raw = d["label"]
            rel_z = d["pos_rel"][1]

            # Maparea Etichetelor și Culorilor (Atenție: OpenCV = BGR)
            if lbl_raw in ['car', 'truck', 'bus']:
                tag, color = "MASINA", (255, 150, 100) # Albastru
            elif lbl_raw == 'person':
                tag, color = "OM", (255, 255, 0) # Cyan
            elif lbl_raw == 'stop sign':
                tag, color = "STOP", (0, 0, 255) # Roșu
            elif lbl_raw == 'priority_sign':
                tag, color = "PRIORITATE", (0, 215, 255) # Galben/Auriu
            elif lbl_raw == 'restriction_sign':
                tag, color = "INTERZIS", (0, 0, 255) # Roșu pur
            elif lbl_raw == 'traffic light':
                tl_c = d.get("tl_color", "NECUNOSCUT")
                tag = f"SEMAFOR [{tl_c}]"
                if tl_c == "ROSU": color = (0, 0, 255)
                elif tl_c == "VERDE": color = (0, 255, 0)
                elif tl_c == "GALBEN": color = (0, 255, 255)
                else: color = (200, 200, 200)
            else:
                tag, color = "OBIECT", (255, 255, 255)

            # Desenare Bounding Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Desenare Text peste obiect
            cv2.putText(frame, f"{tag} | {rel_z}m", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 3. EXPORT DATE (Fix la 0.5 secunde, fără a bloca randerele)
        current_time = time.time()
        if current_time - last_save_time >= 0.5:
            clean_objects = []
            for o in detections:
                obj_clean = {
                    "label": o["label"], 
                    "pos_rel": [float(o["pos_rel"][0]), float(o["pos_rel"][1])]
                }
                if "tl_color" in o: 
                    obj_clean["tl_color"] = o["tl_color"]
                
                clean_objects.append(obj_clean)
                
            data_to_send = {
                "timestamp": round(current_time, 3),
                "decisions": decisions,
                "lane_geometry": lanes,
                "objects": clean_objects
            }
            
            with open(f"{output_dir}/data.json", "w") as f:
                json.dump(data_to_send, f, indent=4)
            
            with open(f"{output_dir}/system.log", "a") as log:
                log.write(f"[{round(current_time, 2)}] RISK: {decisions['risk_level']} | BRAKE: {decisions['brake_decision']}\n")
            
            last_save_time = current_time

        # 4. AFISARE STARE SISTEM (Brake status)
        status_color = (0, 0, 255) if decisions['risk_level'] == 'high' else (0, 255, 0)
        cv2.putText(frame, f"STARE: {decisions['brake_decision'].upper()}", (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)

        cv2.imshow('Magna AI - Heads Up Display', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()