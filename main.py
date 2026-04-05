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

    print("Sistem AI pornit. Procesare video în curs...")
    print("Nu uita să deschizi renderer_2d.py într-un terminal separat!")

    # Setăm dimensiunea ferestrei OpenCV
    cv2.namedWindow('Magna AI - Camera Feed', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Magna AI - Camera Feed', 1280, 720)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Procesare finalizată sau eroare la citirea cadrului.")
            break

        # Redimensionăm imaginea pentru a rula fluid și fără lag
        frame = cv2.resize(frame, (1280, 720))

        # 1. PERCEPȚIE: Analizăm cadrul (Obiecte + Geometrie Benzi stabilizată)
        detections, lanes = eye.analyze(frame)
        
        # 2. LOGICĂ: Decizii bazate pe obiectele găsite (Frână > Bandă > Viteză)
        decisions = brain.update(detections)

        # 3. VIZUALIZARE (Desenăm cutiile pe video)
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            color = (0, 255, 0) if d['label'] == 'car' else (0, 165, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{d['label']} {d['pos_rel'][1]:.1f}m", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 4. EXPORT DATE (La fiecare 0.5 secunde)
        current_time = time.time()
        if current_time - last_save_time >= 0.5:
            
            # Curățăm tipurile de date pentru obiecte (ca să nu dea eroare de ndarray)
            clean_objects = []
            for o in detections:
                clean_objects.append({
                    "label": o["label"],
                    "pos_rel": [float(o["pos_rel"][0]), float(o["pos_rel"][1])] 
                })

            # FIX: Preluăm direct dicționarul de benzi trimis de perception.py
            # Dacă dintr-un motiv anume este None, dăm niște valori sigure (Safe Default)
            clean_lanes = lanes if lanes else {"left_offset": -150, "right_offset": 150}

            # Pachetul de date care pleacă spre renderer-ul 2D
            data_to_send = {
                "timestamp": round(current_time, 3),
                "decisions": decisions,
                "lane_geometry": clean_lanes,
                "objects": clean_objects
            }
            
            with open(f"{output_dir}/data.json", "w") as f:
                json.dump(data_to_send, f, indent=4)
            
            with open(f"{output_dir}/system.log", "a") as log:
                log.write(f"[{round(current_time, 2)}] RISK: {decisions['risk_level']} | BRAKE: {decisions['brake_decision']}\n")
            
            last_save_time = current_time

        # Status pe video
        status_color = (0, 0, 255) if decisions['risk_level'] == 'high' else (0, 255, 0)
        cv2.putText(frame, f"ACTIUNE: {decisions['brake_decision'].upper()}", (40, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)

        cv2.imshow('Magna AI - Camera Feed', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()