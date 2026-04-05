import pygame
import json
import os

def main_renderer():
    pygame.init()
    # Fereastră pentru simularea de deasupra (Bird's Eye View)
    screen = pygame.display.set_mode((600, 800))
    clock = pygame.time.Clock()
    
    # Scale: 1 metru = 20 pixeli
    SCALE = 20 
    OFFSET_X, OFFSET_Y = 300, 700 # Poziția mașinii noastre (jos, centru)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        screen.fill((50, 50, 50)) # Asfalt
        # Desenăm benzile de circulație (decor)
        pygame.draw.line(screen, (255, 255, 255), (200, 0), (200, 800), 5)
        pygame.draw.line(screen, (255, 255, 255), (400, 0), (400, 800), 5)

        # Mașina Noastră (Ego Vehicle)
        pygame.draw.rect(screen, (0, 0, 255), (OFFSET_X-15, OFFSET_Y-30, 30, 60))

        # Citire date din JSON
        if os.path.exists("output/data.json"):
            try:
                with open("output/data.json", "r") as f:
                    data = json.load(f)
                    
                # Randare obiecte externe din lista de detecții (trebuie adăugate în JSON în main.py)
                for obj in data.get("objects", []):
                    rel_x, rel_z = obj["pos_rel"]
                    # Conversie metri -> pixeli
                    draw_x = OFFSET_X + int(rel_x * SCALE)
                    draw_y = OFFSET_Y - int(rel_z * SCALE)
                    
                    color = (255, 0, 0) if obj["label"] == "car" else (255, 255, 0)
                    pygame.draw.rect(screen, color, (draw_x-15, draw_y-30, 30, 60))
                    
            except: pass

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main_renderer()