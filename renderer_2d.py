import pygame
import json
import os

def main_renderer():
    pygame.init()
    screen = pygame.display.set_mode((800, 800))
    pygame.display.set_caption("Magna 2D - Radar Scalat Corect")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16, bold=True)
    
    EGO_X = 400
    EGO_Y = 700 
    SCALE = 25 
    last_valid_data = {}

    while True:
        screen.fill((30, 30, 35)) 
        
        if os.path.exists("output/data.json"):
            try:
                with open("output/data.json", "r") as f:
                    content = f.read()
                    if content.strip(): 
                        last_valid_data = json.loads(content)
            except: pass

        data = last_valid_data

        if data:
            # --- 1. Randare Benzi (Matematica ta de scalare) ---
            lane_geom = data.get("lane_geometry", {})
            
            # Linia de centru (dublă galbenă)
            center_offset = lane_geom.get("center_line", -250)
            draw_center = EGO_X + int(center_offset * SCALE / (1280 / 2))
            pygame.draw.line(screen, (255, 215, 0), (draw_center - 2, 0), (draw_center - 2, 800), 3)
            pygame.draw.line(screen, (255, 215, 0), (draw_center + 2, 0), (draw_center + 2, 800), 3)

            # Linia din dreapta (albă întreruptă)
            right_offset = lane_geom.get("right_line", 250)
            draw_right = EGO_X + int(right_offset * SCALE / (1280 / 2))
            DASH_LEN, GAP_LEN = 20, 15
            y = 0
            while y < 800:
                pygame.draw.line(screen, (255, 255, 255), (draw_right, y), (draw_right, min(y + DASH_LEN, 800)), 2)
                y += DASH_LEN + GAP_LEN

            # --- 2. Randare Obiecte ---
            for obj in data.get("objects", []):
                rel_x, rel_z = obj["pos_rel"]
                obj_x = EGO_X + int(rel_x * SCALE)
                obj_y = EGO_Y - int(rel_z * SCALE)
                
                if 0 < obj_x < 800 and 0 < obj_y < 800:
                    lbl_raw = obj["label"]
                    if lbl_raw in ['car', 'truck', 'bus']: color = (100, 150, 255)
                    elif lbl_raw == 'person': color = (0, 255, 255)
                    elif lbl_raw in ['stop sign', 'restriction_sign']: color = (255, 50, 50)
                    elif lbl_raw == 'priority_sign': color = (255, 215, 0)
                    elif lbl_raw == 'traffic light':
                        tl_c = obj.get("tl_color", "NECUNOSCUT")
                        if tl_c == "ROSU": color = (255, 0, 0)
                        elif tl_c == "VERDE": color = (0, 255, 0)
                        elif tl_c == "GALBEN": color = (255, 255, 0)
                        else: color = (200, 200, 200)
                    else: color = (255, 255, 255)

                    pygame.draw.rect(screen, color, (obj_x - 15, obj_y - 30, 30, 60), border_radius=4)

            # UI Status
            brake = data.get("decisions", {}).get("brake_decision", "N/A").upper()
            c = (255, 50, 50) if brake in ["STRONG", "LIGHT"] else (50, 255, 50)
            screen.blit(font.render(f"STARE: {brake}", True, c), (20, 20))

        # EGO
        pygame.draw.rect(screen, (0, 255, 100), (EGO_X - 15, EGO_Y - 30, 30, 60), border_radius=4)
        screen.blit(font.render("EGO", True, (255, 255, 255)), (EGO_X - 15, EGO_Y + 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return
            
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main_renderer()