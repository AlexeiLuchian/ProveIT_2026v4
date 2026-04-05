import pygame, json, os

def main_renderer():
    pygame.init()
    screen = pygame.display.set_mode((800, 800))
    pygame.display.set_caption("Magna 2D - Professional Radar")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18, bold=True)
    EGO_X, EGO_Y, SCALE = 400, 700, 15
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        screen.fill((20, 20, 25))
        if os.path.exists("output/data.json"):
            try:
                with open("output/data.json", "r") as f: data = json.load(f)
                
                # 1. Asfalt Vizual
                road_left = EGO_X - 175
                road_right = EGO_X + 175
                pygame.draw.rect(screen, (50, 50, 55), (road_left, 0, road_right - road_left, 800))

                lanes = data.get("lane_geometry", {})
                l_m = (lanes.get("center_line", -250) * 3.5 / 450)
                r_m = (lanes.get("right_line", 250) * 3.5 / 450)

                # 2. Linia Stânga (Galbenă)
                draw_left = EGO_X + int(l_m*SCALE)
                pygame.draw.line(screen, (255, 200, 0), (draw_left-2, 0), (draw_left-2, 800), 2)
                pygame.draw.line(screen, (255, 200, 0), (draw_left+2, 0), (draw_left+2, 800), 2)

                # 3. Linia Dreapta (Albă Întreruptă)
                draw_right = EGO_X + int(r_m*SCALE)
                y = 0
                while y < 800:
                    pygame.draw.line(screen, (220,220,220), (draw_right, y), (draw_right, min(y+20, 800)), 3)
                    y += 35

                # 4. Obiecte
                for o in data.get("objects", []):
                    rx, rz, lbl = o["pos_rel"][0], o["pos_rel"][1], o["label"]
                    c = (0, 102, 204) if lbl in ['car','bus','truck'] else (255, 255, 255)
                    if lbl == 'traffic light': c = (100, 100, 100)
                    pygame.draw.rect(screen, c, (EGO_X + int(rx*SCALE) - 10, EGO_Y - int(rz*SCALE) - 20, 20, 40), border_radius=4)
                
                # 5. UI Decizii
                decisions = data.get("decisions", {})
                speed_d = decisions.get("speed_decision", "?").upper()
                lane_d  = decisions.get("lane_decision", "?").upper()
                brake_d = decisions.get("brake_decision", "none")
                
                screen.blit(font.render(f"SPEED: {speed_d}", True, (255,255,80)), (20, 20))
                screen.blit(font.render(f"LANE:  {lane_d}",  True, (80,180,255)), (20, 45))
                screen.blit(font.render(f"BRAKE: {brake_d.upper()}", True, (255,80,80) if brake_d!="none" else (80,255,80)), (20, 70))

                # 6. EGO Car Reactiv
                ego_col = (255,50,50) if brake_d=="strong" else (255,180,0) if brake_d=="light" else (0,255,100)
                pygame.draw.rect(screen, ego_col, (EGO_X-15, EGO_Y-30, 30, 60), border_radius=4)
                screen.blit(font.render("EGO", True, (255,255,255)), (EGO_X-15, EGO_Y+35))

            except: pass

        pygame.display.flip(); clock.tick(30)

if __name__ == "__main__": main_renderer()