import pygame
import json
import os

def main_renderer():
    pygame.init()
    screen = pygame.display.set_mode((800, 800))
    pygame.display.set_caption("Magna 2D - Bird's Eye View")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)
    
    # Mașina ta este ancora (EGO). Totul se randează în funcție de ea.
    EGO_X = 400
    EGO_Y = 700 
    SCALE = 25 # Metri spre pixeli pentru obiecte

    while True:
        screen.fill((30, 30, 30)) # Asfalt
        
        if os.path.exists("output/data.json"):
            try:
                with open("output/data.json", "r") as f:
                    data = json.load(f)
                
                # --- 1. RANDAREA BENZILOR (Dynamic din JSON) ---
                lanes = data.get("lane_geometry", {})
                if lanes:
                    # Folosim un factor de scalare vizuală pentru lățimea din video (aprox / 3)
                    draw_left_x = EGO_X + int(lanes["left_lane"] / 3)
                    draw_right_x = EGO_X + int(lanes["right_lane"] / 3)
                    
                    # Desenăm banda noastră (albă)
                    pygame.draw.line(screen, (255, 255, 255), (draw_left_x, 0), (draw_left_x, 800), 4)
                    pygame.draw.line(screen, (255, 255, 255), (draw_right_x, 0), (draw_right_x, 800), 4)
                    
                    # Desenăm contururile exterioare (pentru efect vizual de stradă mare)
                    lane_width = draw_right_x - draw_left_x
                    pygame.draw.line(screen, (100, 100, 100), (draw_left_x - lane_width, 0), (draw_left_x - lane_width, 800), 2)
                    pygame.draw.line(screen, (100, 100, 100), (draw_right_x + lane_width, 0), (draw_right_x + lane_width, 800), 2)

                # --- 2. RANDAREA MAȘINII TALE (Fixă) ---
                pygame.draw.rect(screen, (0, 150, 255), (EGO_X - 15, EGO_Y - 30, 30, 60))
                
                # --- 3. RANDAREA OBIECTELOR EXTERNE ---
                for obj in data.get("objects", []):
                    rel_x, rel_z = obj["pos_rel"]
                    
                    # Poziționăm obiectul relativ la mașina noastră
                    obj_x = EGO_X + int(rel_x * SCALE)
                    obj_y = EGO_Y - int(rel_z * SCALE)
                    
                    # Afișăm doar dacă este în raza ecranului
                    if 0 < obj_x < 800 and 0 < obj_y < 800:
                        color = (255, 50, 50) if "car" in obj["label"] else (255, 255, 0)
                        pygame.draw.rect(screen, color, (obj_x - 15, obj_y - 30, 30, 60))
                        screen.blit(font.render(f"{obj['label']} {rel_z}m", True, (255,255,255)), (obj_x + 20, obj_y - 10))

                # --- 4. UI: STARE DECIZIE ---
                brake = data.get("decisions", {}).get("brake_decision", "N/A").upper()
                c = (255, 0, 0) if brake in ["STRONG", "LIGHT"] else (0, 255, 0)
                screen.blit(font.render(f"FRÂNĂ: {brake}", True, c), (20, 20))

            except Exception as e:
                pass # Ignorăm conflictele de citire din timpul salvării JSON-ului

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return
            
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main_renderer()