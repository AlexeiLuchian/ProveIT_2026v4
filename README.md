# ProveIT 2026

Sistem de asistență la conducere autonomă care procesează în timp real un flux video de cameră frontală.

## Funcționalități

- Detecție obiecte din trafic cu YOLOv8 (mașini, camioane, autobuze, pietoni, biciclete, motociclete, semafoare, indicatoare STOP)
- Estimare distanță și viteză relativă per obiect
- Detecție benzi de circulație (sliding window + Sobel + bird's-eye warp)
- Detecție culoare semafor (HSV)
- Estimare suprafață drum și vizibilitate (condiții ceață)
- Decizii de conducere: frânare, viteză, schimbare bandă
- Randare 2D radar (Pygame)
- Randare 3D scena (OpenGL)
- Dashboard web live (Streamlit)

## Structura proiectului

```
core/               # Percepție și logică
  perception.py     # YOLO, detecție benzi, suprafață drum, ceață
  logic.py          # Decizii de conducere
rendering/          # Randare
  renderer_2d.py    # Radar 2D Pygame
  renderer_3d.py    # Scena 3D OpenGL
main.py             # Pipeline principal + DataBus observer
dashboard.py        # Dashboard Streamlit (loguri + JSON live)
prezentare.md       # Documentatie completa pentru prezentare
```

## Instalare

```bash
uv sync
```

Sau:

```bash
pip install opencv-contrib-python pygame ultralytics streamlit
```

Modelul `yolov8n.pt` se descarcă automat la primul rulare.

## Rulare

```bash
# Pipeline principal (fereastra cv2 cu HUD)
python main.py

# Radar 2D
python rendering/renderer_2d.py

# Scena 3D
python rendering/renderer_3d.py

# Dashboard web → http://localhost:8501
.venv/bin/python -m streamlit run dashboard.py
```

Din dashboard se pot porni toate componentele cu butoanele Play / 2D / 3D.
