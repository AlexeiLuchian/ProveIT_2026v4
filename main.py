import cv2, time, json, os
from perception import PerceptionSystem
from logic import DrivingLogic

def main():
    cap = cv2.VideoCapture("video_test.mp4")
    eye, brain = PerceptionSystem(), DrivingLogic()
    last_save = 0
    if not os.path.exists("output"): os.makedirs("output")
    
    cv2.namedWindow('Magna HUD', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Magna HUD', 1280, 720)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.resize(frame, (1280, 720))
        
        detections, lanes = eye.analyze(frame)
        decisions = brain.update(detections)

        # Desenare Video HUD
        for d in detections:
            x1, y1, x2, y2 = d["box"]
            lbl, rz = d["label"], d["pos_rel"][1]
            c = (255,150,100) if lbl in ['car','bus','truck'] else (0,255,0)
            if 'sign' in lbl or lbl == 'stop sign': c = (0,0,255)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), c, 2)
            cv2.putText(frame, f"{lbl.upper()} {rz}m", (x1, y1-10), 1, 1.2, c, 2)

        # Export (la 0.5s) + Log cu Motiv
        current_time = time.time()
        if current_time - last_save >= 0.5:
            with open("output/data.json", "w") as f:
                json.dump({"decisions": decisions, "lane_geometry": lanes, "objects": detections}, f, indent=4)
            
            # Calcul Motiv Decizie
            nearest = min(detections, key=lambda x: x["pos_rel"][1], default=None)
            reason = f"{nearest['label']} la {nearest['pos_rel'][1]}m" if nearest else "drum liber"
            
            with open("output/system.log", "a") as log:
                log.write(f"[{round(current_time,2)}] RISK:{decisions['risk_level']} | BRAKE:{decisions['brake_decision']} | SPEED:{decisions['speed_decision']} | REASON:{reason}\n")
            
            last_save = current_time

        status_c = (0,0,255) if decisions['risk_level'] == 'high' else (0,255,0)
        cv2.putText(frame, f"BRAKE: {decisions['brake_decision'].upper()}", (20, 40), 1, 2, status_c, 3)

        cv2.imshow('Magna HUD', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
        
    cap.release(); cv2.destroyAllWindows()

if __name__ == "__main__": main()