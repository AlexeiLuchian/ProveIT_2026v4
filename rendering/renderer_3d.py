import pygame, json, os, math, pathlib
from pygame.locals import *
from OpenGL.GL import *

DATA_JSON = pathlib.Path(__file__).parent.parent / "output" / "data.json"

# Culori RGB OpenGL per clasă (valori 0.0–1.0)
OBJ_COLORS_3D = {
    "car":           (0.24, 0.59, 1.00),
    "truck":         (1.00, 0.51, 0.24),
    "bus":           (0.78, 0.24, 0.78),
    "person":        (0.00, 1.00, 1.00),
    "bicycle":       (0.24, 0.86, 0.24),
    "motorcycle":    (1.00, 0.78, 0.00),
    "stop sign":     (0.90, 0.10, 0.10),
    "traffic light": (0.40, 0.40, 0.40),
}

# Dimensiuni (w, h, d) în metri pentru fiecare clasă
OBJ_DIMS_3D = {
    "car":           (1.1, 0.7, 2.2),
    "truck":         (1.3, 1.5, 4.5),
    "bus":           (1.5, 1.8, 6.0),
    "person":        (0.3, 0.9, 0.3),
    "bicycle":       (0.3, 0.6, 0.8),
    "motorcycle":    (0.5, 0.8, 1.2),
    "stop sign":     (0.4, 0.4, 0.05),
    "traffic light": (0.3, 1.0, 0.3),
}


def setup_perspective(fov, aspect, near, far):
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    top   = near * math.tan(math.radians(fov) / 2.0)
    right = top * aspect
    glFrustum(-right, right, -top, top, near, far)
    glMatrixMode(GL_MODELVIEW)


def draw_styled_cube(x, y, z, w, h, d, color):
    glPushMatrix()
    glTranslatef(x, y, z); glScalef(w, h, d); glColor3f(*color)
    vertices = [[1,1,-1],[1,-1,-1],[-1,-1,-1],[-1,1,-1],
                [1,1, 1],[1,-1, 1],[-1,-1, 1],[-1,1, 1]]
    faces    = [(0,1,2,3),(3,2,6,7),(7,6,5,4),(4,5,1,0),(1,5,6,2),(4,0,3,7)]
    glBegin(GL_QUADS)
    for f in faces:
        for v in f: glVertex3fv(vertices[v])
    glEnd()
    glPopMatrix()


def main_3d():
    pygame.init()
    display = (1024, 768)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Magna 3D - Full Logic Render")

    setup_perspective(60, display[0] / display[1], 0.1, 200.0)

    brake_trails  = []
    skid_offset   = 0.0
    skid_velocity = 0.0
    prev_brake    = "none"
    last_data     = {}

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glLoadIdentity()
        glTranslatef(0.0, -5.0, -15.0)
        glRotatef(20, 1, 0, 0)

        # Citire JSON
        if DATA_JSON.exists():
            try:
                with open(DATA_JSON, "r") as f:
                    last_data = json.load(f)
            except Exception:
                pass

        data      = last_data
        decisions = data.get("decisions", {})
        brake     = decisions.get("brake_decision", "none")

        # ── Asfalt ──────────────────────────────────────────────────────────
        glBegin(GL_QUADS)
        glColor3f(0.12, 0.12, 0.14)
        glVertex3f(-25, 0, 10);  glVertex3f(25, 0, 10)
        glVertex3f(25, 0, -150); glVertex3f(-25, 0, -150)
        glEnd()

        # ── Linii de bandă ───────────────────────────────────────────────────
        lanes = data.get("lane_geometry", {})
        l_m   = lanes.get("center_line", -250) * 3.5 / 450
        r_m   = lanes.get("right_line",   250) * 3.5 / 450

        # Galbenă dublă (contrasens)
        glColor3f(1.0, 0.8, 0.0)
        for offset in [-0.12, 0.12]:
            glBegin(GL_QUADS)
            glVertex3f(l_m+offset-0.05, 0.02,  10)
            glVertex3f(l_m+offset+0.05, 0.02,  10)
            glVertex3f(l_m+offset+0.05, 0.02, -150)
            glVertex3f(l_m+offset-0.05, 0.02, -150)
            glEnd()

        # Albă întreruptă (banda curentă)
        glColor3f(1.0, 1.0, 1.0)
        z = 10.0
        while z > -150:
            glBegin(GL_QUADS)
            glVertex3f(r_m-0.08, 0.02, z)
            glVertex3f(r_m+0.08, 0.02, z)
            glVertex3f(r_m+0.08, 0.02, z-3.0)
            glVertex3f(r_m-0.08, 0.02, z-3.0)
            glEnd()
            z -= 9.0

        # ── Obiecte detectate ────────────────────────────────────────────────
        for o in data.get("objects", []):
            lbl = o["label"]
            rx, rz = o["pos_rel"][0], o["pos_rel"][1]

            base_color = OBJ_COLORS_3D.get(lbl, (0.8, 0.8, 0.8))
            dims = OBJ_DIMS_3D.get(lbl, (0.8, 0.8, 0.8))
            w_d, h_d, d_d = dims

            if lbl == "traffic light":
                draw_styled_cube(rx, h_d/2, -rz, w_d, h_d/2, d_d, (0.35, 0.35, 0.35))
                tc  = o.get("tl_color", "")
                led = (1,0,0) if tc=="ROSU" else (0,1,0) if tc=="VERDE" else (1,1,0) if tc=="GALBEN" else (0.3,0.3,0.3)
                draw_styled_cube(rx, h_d + 0.2, -rz - 0.1, 0.2, 0.2, 0.2, led)
            else:
                draw_styled_cube(rx, h_d/2, -rz, w_d, h_d/2, d_d, base_color)

        # ── Urme de frânare (+5p bonus) ──────────────────────────────────────
        if brake == "strong":
            brake_trails.append(skid_offset)
        if len(brake_trails) > 40:
            brake_trails.pop(0)

        glColor3f(0.04, 0.04, 0.04)
        for i, sx in enumerate(brake_trails):
            z_pos = float(i) * 0.3
            for tx in [sx - 0.35, sx + 0.35]:
                glBegin(GL_QUADS)
                glVertex3f(tx-0.08, 0.01, z_pos);     glVertex3f(tx+0.08, 0.01, z_pos)
                glVertex3f(tx+0.08, 0.01, z_pos+0.2); glVertex3f(tx-0.08, 0.01, z_pos+0.2)
                glEnd()

        # ── EGO + derapaj (+5p bonus) ────────────────────────────────────────
        if brake == "strong" and prev_brake != "strong":
            skid_velocity = 0.35
        prev_brake = brake

        skid_offset   += skid_velocity
        skid_velocity *= 0.50
        skid_offset   *= 0.70
        if abs(skid_velocity) < 0.001: skid_velocity = 0.0
        if abs(skid_offset)   < 0.01:  skid_offset   = 0.0

        ego_col = (1.0,0.1,0.1) if brake=="strong" else (1.0,0.7,0.0) if brake=="light" else (0.0,1.0,0.4)
        draw_styled_cube(skid_offset, 0.4, 0, 1.1, 0.4, 2.2, ego_col)

        pygame.display.flip()
        pygame.time.Clock().tick(30)


if __name__ == '__main__':
    main_3d()
