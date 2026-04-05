import pygame
from pygame.locals import *
from OpenGL.GL import *
import json
import os
import math

def setup_perspective(fov, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov) / 2.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    top = near * math.tan(math.radians(fov) / 2.0)
    right = top * aspect
    glFrustum(-right, right, -top, top, near, far)
    glMatrixMode(GL_MODELVIEW)

def draw_cube(x, y, z, w, h, d, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(w, h, d)
    glColor3f(*color)
    # Cub standard 1x1x1 unități
    vertices = [
        [1, 1, -1], [1, -1, -1], [-1, -1, -1], [-1, 1, -1],
        [1, 1, 1], [1, -1, 1], [-1, -1, 1], [-1, 1, 1]
    ]
    faces = [(0,1,2,3), (3,2,6,7), (7,6,5,4), (4,5,1,0), (1,5,6,2), (4,0,3,7)]
    glBegin(GL_QUADS)
    for face in faces:
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()
    glPopMatrix()

def main_3d():
    pygame.init()
    display = (1024, 768)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Magna 3D - Proiectie Corectata")

    setup_perspective(60, (display[0]/display[1]), 0.1, 200.0)
    
    clock = pygame.time.Clock()
    last_valid_data = {}

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glLoadIdentity()

        # --- CAMERA (Ancorată în spatele mașinii EGO) ---
        # Ne ridicăm la 5 metri înălțime și stăm la 10 metri în spatele mașinii (Z pozitiv)
        # Privim spre punctul (0, 0, -20) care este în fața mașinii
        glTranslatef(0.0, -5.0, -15.0) 
        glRotatef(20, 1, 0, 0) # Înclinăm camera să vedem drumul

        if os.path.exists("output/data.json"):
            try:
                with open("output/data.json", "r") as f:
                    content = f.read()
                    if content.strip():
                        last_valid_data = json.loads(content)
            except: pass

        data = last_valid_data

        # 1. DESENĂM ASFALTUL (Până la 100 metri în față)
        glBegin(GL_QUADS)
        glColor3f(0.1, 0.1, 0.12)
        glVertex3f(-20, 0, 10)    # Spatele mașinii
        glVertex3f(20, 0, 10)
        glVertex3f(20, 0, -150)  # Depărtare (Z negativ în OpenGL)
        glVertex3f(-20, 0, -150)
        glEnd()

        # 2. MAȘINA EGO (Poziția 0,0,0)
        # O desenăm un pic mai sus (y=0.6) ca să nu intre în asfalt
        draw_cube(0, 0.6, 0, 1.1, 0.6, 2.2, (0.0, 1.0, 0.2))

        if data:
            lane_geom = data.get("lane_geometry", {})
            # Folosim metri reali (3.5m bandă)
            l_x, r_x = -1.75, 1.75

            # Linie Centru (Galbenă)
            glColor3f(1.0, 0.8, 0.0)
            glBegin(GL_QUADS)
            glVertex3f(l_x-0.1, 0.05, 10); glVertex3f(l_x+0.1, 0.05, 10)
            glVertex3f(l_x+0.1, 0.05, -150); glVertex3f(l_x-0.1, 0.05, -150)
            glEnd()

            # Linie Dreapta (Albă întreruptă)
            glColor3f(1.0, 1.0, 1.0)
            for z in range(10, -150, -10): # Mergem spre înainte (Z negativ)
                glBegin(GL_QUADS)
                glVertex3f(r_x-0.1, 0.05, z); glVertex3f(r_x+0.1, 0.05, z)
                glVertex3f(r_x+0.1, 0.05, z-5); glVertex3f(r_x-0.1, 0.05, z-5)
                glEnd()

            # 3. RANDARE OBIECTE DIN JSON
            for obj in data.get("objects", []):
                rx, rz = obj["pos_rel"]
                lbl = obj["label"]
                
                # --- FIX CRITIC PENTRU PRECIZIE ---
                # În JSON rz este distanța în față (ex: 15 metri).
                # În OpenGL, înainte = Z negativ. Deci desenăm la -rz.
                draw_z = -rz 

                if lbl in ['car', 'truck', 'bus']: col = (0.2, 0.4, 1.0)
                elif lbl == 'person': col = (0.0, 1.0, 1.0)
                elif lbl == 'traffic light':
                    tc = obj.get("tl_color", "")
                    col = (1,0,0) if tc=="ROSU" else ((0,1,0) if tc=="VERDE" else (0.9,0.9,0))
                else: col = (1, 0.2, 0.2)

                # Desenăm cubul la coordonatele transformate
                draw_cube(rx, 0.8, draw_z, 1.0, 0.8, 1.8, col)

        pygame.display.flip()
        clock.tick(30)

if __name__ == '__main__':
    main_3d()