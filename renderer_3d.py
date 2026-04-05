import pygame, json, os, math
from pygame.locals import *
from OpenGL.GL import *

def setup_perspective(fov, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov) / 2.0)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    top = near * math.tan(math.radians(fov) / 2.0); right = top * aspect
    glFrustum(-right, right, -top, top, near, far); glMatrixMode(GL_MODELVIEW)

def draw_styled_cube(x, y, z, w, h, d, color):
    glPushMatrix()
    glTranslatef(x, y, z); glScalef(w, h, d); glColor3f(*color)
    vertices = [[1,1,-1],[1,-1,-1],[-1,-1,-1],[-1,1,-1],[1,1,1],[1,-1,1],[-1,-1,1],[-1,1,1]]
    faces = [(0,1,2,3), (3,2,6,7), (7,6,5,4), (4,5,1,0), (1,5,6,2), (4,0,3,7)]
    glBegin(GL_QUADS)
    for f in faces: 
        for v in f: glVertex3fv(vertices[v])
    glEnd(); glPopMatrix()

def render_text(text, x, y, color):
    """Printează HUD-ul 2D peste scena 3D OpenGL"""
    font = pygame.font.SysFont("Arial", 22, bold=True)
    text_surf = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surf, "RGBA", True)
    glWindowPos2d(x, y)
    glDrawPixels(text_surf.get_width(), text_surf.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)

def main_3d():
    pygame.init(); display = (1024, 768)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Magna 3D - Full Logic Render")
    
    setup_perspective(60, (display[0]/display[1]), 0.1, 200.0)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT); glEnable(GL_DEPTH_TEST)
        glLoadIdentity()
        
        # CAMERA: Aceea pe care o iubeai (din spate, unghi perfect)
        glTranslatef(0.0, -5.0, -15.0) 
        glRotatef(20, 1, 0, 0) 

        decisions = {}
        if os.path.exists("output/data.json"):
            try:
                with open("output/data.json", "r") as f: 
                    data = json.load(f)
                    decisions = data.get("decisions", {})
                
                # Asfalt
                glBegin(GL_QUADS); glColor3f(0.12, 0.12, 0.14); glVertex3f(-25,0,10); glVertex3f(25,0,10); glVertex3f(25,0,-150); glVertex3f(-25,0,-150); glEnd()
                
                lanes = data.get("lane_geometry", {})
                l_m = (lanes.get("center_line", -250) * 3.5 / 450)
                r_m = (lanes.get("right_line", 250) * 3.5 / 450)
                
                # Linia galbenă DUBLE
                glColor3f(1.0, 0.8, 0.0)
                for offset in [-0.12, 0.12]:
                    glBegin(GL_QUADS)
                    glVertex3f(l_m+offset-0.05, 0.02, 10);  glVertex3f(l_m+offset+0.05, 0.02, 10)
                    glVertex3f(l_m+offset+0.05, 0.02, -150); glVertex3f(l_m+offset-0.05, 0.02, -150)
                    glEnd()

                # Linia albă ÎNTRERUPTĂ
                glColor3f(1.0, 1.0, 1.0)
                z = 10
                while z > -150:
                    glBegin(GL_QUADS)
                    glVertex3f(r_m-0.08, 0.02, z);      glVertex3f(r_m+0.08, 0.02, z)
                    glVertex3f(r_m+0.08, 0.02, z-3.0);  glVertex3f(r_m-0.08, 0.02, z-3.0)
                    glEnd()
                    z -= 9.0

                # Obiecte
                for o in data.get("objects", []):
                    rx, rz, lbl = o["pos_rel"][0], o["pos_rel"][1], o["label"]
                    if lbl in ['car', 'bus', 'truck']:
                        c = (0.0, 0.4, 0.8)
                        w, h, d = (1.1, 0.7, 2.0) if lbl == 'car' else (1.4, 1.4, 4.5)
                        draw_styled_cube(rx, h/2, -rz, w, h/2, d, c)
                    elif lbl == 'traffic light':
                        tc = o.get("tl_color", "")
                        l_c = (1,0,0) if tc == "ROSU" else (0,1,0) if tc == "VERDE" else (1,1,0)
                        draw_styled_cube(rx, 2.0, -rz, 0.3, 1.0, 0.3, (0.4, 0.4, 0.4)) # Corp gri
                        draw_styled_cube(rx, 2.8, -rz-0.1, 0.2, 0.2, 0.2, l_c) # Lumina corectă
                    elif 'sign' in lbl:
                        draw_styled_cube(rx, 1.5, -rz, 0.6, 0.6, 0.1, (1, 1, 1))

            except: pass

        # EGO Car (Colorat după frână)
        brake = decisions.get("brake_decision", "none")
        ego_color = (1.0, 0.1, 0.1) if brake == "strong" else (1.0, 0.7, 0.0) if brake == "light" else (0.0, 1.0, 0.4)
        draw_styled_cube(0, 0.4, 0, 1.1, 0.4, 2.2, ego_color)

        # TEXT HUD (Decizii 3D)
        speed_t = decisions.get("speed_decision","?").upper()
        lane_t  = decisions.get("lane_decision","?").upper()
        brake_t = decisions.get("brake_decision","?").upper()
        
        # Coordonatele Y pleacă de jos în sus în glWindowPos2d
        render_text(f"BRAKE: {brake_t}", 20, 720, (255,80,80) if brake_t!="NONE" else (80,255,80))
        render_text(f"SPEED: {speed_t}", 20, 690, (255,255,80))
        render_text(f"LANE:  {lane_t}", 20, 660, (80,200,255))

        pygame.display.flip(); pygame.time.Clock().tick(30)

if __name__ == '__main__': main_3d()