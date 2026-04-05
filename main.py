import cv2
import time
import json
import os
from perception import PerceptionSystem
from logic import DrivingLogic

def main():
    # Sursa video conform regulamentului [cite: 72-76]
    video_path = "video_test.mp4" 
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Eroare: Nu s-a putut deschide fisierul {video_path}")
        return

    # Initializam modulele
    eye = PerceptionSystem()
    brain = DrivingLogic()
    
    # Setari pentru export [cite: 10, 40]
    last_output_time = 0
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Configurare fereastra (fix pentru eroarea de font/dimensiune)
    window_name = 'Magna AI - Main Processor'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    print("Sistem pornit. Procesare in curs...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Perceptie: Detectam obiecte si calculam coordonatele relative (distanta)
        # Acopera criteriul "Acuratetea Perceptiei" 
        detections = eye.analyze(frame)
        
        # 2. Logica: Luam decizii (Frena > Banda > Viteza) 
        # Acopera criteriul "Corectitudinea Deciziilor" 
        decisions = brain.update(detections)

        # 3. Vizualizare Overlay (UX/Explicabilitate - 10p) 
        for obj in detections:
            x1, y1, x2, y2 = obj["box"]
            rel_x, rel_z = obj["pos_rel"]
            
            # Desenam bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Afisam eticheta si distanta estimata (Z)
            label_text = f"{obj['label']} | Dist: {rel_z}m"
            cv2.putText(frame, label_text, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 4. Export Date la interval de 0.5 secunde (Obligatoriu) [cite: 39, 40]
        current_time = time.time()
        if current_time - last_output_time >= 0.5:
            # Pachetul de date pentru Renderer-ul 2D (JSON) [cite: 24, 39]
            output_package = {
                "timestamp": round(current_time, 3),
                "decisions": decisions,
                "objects": [
                    {"label": o["label"], "pos_rel": o["pos_rel"]} 
                    for o in detections
                ]
            }
            
            # Salvare JSON 
            with open(f"{output_dir}/data.json", "w") as f:
                json.dump(output_package, f, indent=4)
            
            # Salvare Log (Nivel risc si decizii frana) [cite: 39, 45, 46, 47]
            with open(f"{output_dir}/system.log", "a") as log:
                log_entry = (f"[{round(current_time, 1)}] "
                             f"RISK: {decisions['risk_level']} | "
                             f"BRAKE: {decisions['brake_decision']} | "
                             f"SPEED: {decisions['speed_decision']}\n")
                log.write(log_entry)
            
            last_output_time = current_time

        # Afisare UI stare sistem pe video
        status_color = (0, 0, 255) if decisions['risk_level'] == 'high' else (0, 255, 0)
        cv2.putText(frame, f"BRAKE: {decisions['brake_decision'].upper()}", (50, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)

        cv2.imshow(window_name, frame)

        # Iesire la tasta 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Procesare finalizata. Datele sunt salvate in folderul '{output_dir}'.")

if __name__ == "__main__":
    main()