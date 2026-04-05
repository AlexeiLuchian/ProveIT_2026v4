import pygame, json, os

# Culori RGB per clasă (Pygame folosește RGB, nu BGR)
OBJ_COLORS = {
    "car":           ( 60, 150, 255),   # albastru deschis
    "truck":         (255, 130,  60),   # portocaliu
    "bus":           (200,  60, 200),   # mov
    "person":        (  0, 255, 255),   # cyan
    "bicycle":       ( 60, 220,  60),   # verde lime
    "motorcycle":    (255, 200,   0),   # galben
    "stop sign":     (255,  50,  50),   # roșu
    "traffic light": (160, 160, 160),   # gri (default)
}

OBJ_LABELS = {
    "car": "MASINA", "truck": "CAMION", "bus": "AUTOBUS",
    "person": "PIETON", "bicycle": "BICICL", "motorcycle": "MOTO",
    "stop sign": "STOP", "traffic light": "SEMAF",
}

# Dimensiuni vizuale per clasă (w, h) în pixeli pe radar
OBJ_SIZES = {
    "car":        (20, 40),
    "truck":      (24, 55),
    "bus":        (28, 65),
    "person":     (10, 22),
    "bicycle":    (10, 20),
    "motorcycle": (12, 25),
    "stop sign":  (14, 14),
    "traffic light": (10, 22),
}


def main_renderer():
    pygame.init()
    screen = pygame.display.set_mode((800, 800))
    pygame.display.set_caption("Magna 2D - Radar")
    clock  = pygame.font.SysFont("Arial", 14, bold=True)  # font mic pentru labels
    font   = pygame.font.SysFont("Arial", 18, bold=True)
    font_s = pygame.font.SysFont("Arial", 13)
    EGO_X, EGO_Y, SCALE = 400, 700, 15

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        screen.fill((20, 20, 25))

        if os.path.exists("output/data.json"):
            try:
                with open("output/data.json", "r") as f:
                    data = json.load(f)

                # ── Drum ────────────────────────────────────────────────────
                road_left  = EGO_X - 175
                road_right = EGO_X + 175
                pygame.draw.rect(screen, (50, 50, 55),
                                 (road_left, 0, road_right - road_left, 800))
                pygame.draw.line(screen, (70, 70, 75), (road_left,  0), (road_left,  800), 2)
                pygame.draw.line(screen, (70, 70, 75), (road_right, 0), (road_right, 800), 2)

                # ── Linii de bandă ───────────────────────────────────────────
                lanes = data.get("lane_geometry", {})
                l_m   = lanes.get("center_line", -250) * 3.5 / 450
                r_m   = lanes.get("right_line",   250) * 3.5 / 450

                draw_left  = EGO_X + int(l_m * SCALE)
                draw_right = EGO_X + int(r_m * SCALE)

                # Linie galbenă dublă (contrasens)
                pygame.draw.line(screen, (255, 200, 0), (draw_left-2, 0), (draw_left-2, 800), 2)
                pygame.draw.line(screen, (255, 200, 0), (draw_left+2, 0), (draw_left+2, 800), 2)

                # Linie albă dreaptă întreruptă
                y = 0
                while y < 800:
                    pygame.draw.line(screen, (220, 220, 220),
                                     (draw_right, y), (draw_right, min(y+20, 800)), 3)
                    y += 35

                # ── Obiecte detectate ────────────────────────────────────────
                for o in data.get("objects", []):
                    lbl = o["label"]
                    rx, rz = o["pos_rel"]

                    color = OBJ_COLORS.get(lbl, (255, 255, 255))

                    # Semafoarele: culoarea după starea ledului
                    if lbl == "traffic light":
                        tc = o.get("tl_color", "")
                        if tc == "ROSU":   color = (255,  50,  50)
                        elif tc == "VERDE": color = ( 50, 230,  50)
                        elif tc == "GALBEN": color = (255, 220,   0)

                    sx, sy = OBJ_SIZES.get(lbl, (16, 32))
                    ox = EGO_X + int(rx * SCALE) - sx // 2
                    oy = EGO_Y - int(rz * SCALE) - sy
                    pygame.draw.rect(screen, color, (ox, oy, sx, sy), border_radius=3)

                    # Label mic deasupra obiectului
                    tag = OBJ_LABELS.get(lbl, lbl[:5].upper())
                    screen.blit(font_s.render(tag, True, color), (ox, oy - 14))

                # ── Decizii UI ───────────────────────────────────────────────
                decisions = data.get("decisions", {})
                speed_d = decisions.get("speed_decision", "?").upper()
                lane_d  = decisions.get("lane_decision",  "?").upper()
                brake_d = decisions.get("brake_decision", "none")

                screen.blit(font.render(f"SPEED: {speed_d}", True, (255, 255, 80)),  (20, 20))
                screen.blit(font.render(f"LANE:  {lane_d}",  True, (80, 180, 255)), (20, 45))
                screen.blit(font.render(
                    f"BRAKE: {brake_d.upper()}",
                    True, (255, 80, 80) if brake_d != "none" else (80, 255, 80)
                ), (20, 70))

                # ── EGO reactiv ──────────────────────────────────────────────
                ego_col = (255,50,50) if brake_d=="strong" else (255,180,0) if brake_d=="light" else (0,255,100)
                pygame.draw.rect(screen, ego_col, (EGO_X-15, EGO_Y-30, 30, 60), border_radius=4)
                screen.blit(font.render("EGO", True, (255, 255, 255)), (EGO_X-15, EGO_Y+35))

            except Exception:
                pass

        pygame.display.flip()
        pygame.time.Clock().tick(30)


if __name__ == "__main__":
    main_renderer()
