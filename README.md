# ProveIT 2026 — Autonomous Driving Assistance System

> **Built for [ProveIT Techathon 2026](https://proveit.bestis.ro/)**
> This project was our team's competition submission, developed end-to-end within the hackathon timeframe.

A real-time autonomous driving assistance system that processes a front-facing camera feed to detect traffic objects, estimate distances and relative speeds, make driving decisions, and visualize everything simultaneously across three rendering modes.

---

## System Architecture

```
video_test.mp4
      │
      ▼
main.py ──────────────────────────────────────────────────────
  ├─ core/perception.py   → YOLO inference + lane detection + road surface + fog
  ├─ core/logic.py        → driving decisions
  ├─ DataBus (Observer)   → publishes JSON to all subscribers
  └─ output/data.json + output/system.log
            │
            ├──► rendering/renderer_2d.py   (Pygame top-down radar)
            ├──► rendering/renderer_3d.py   (OpenGL 3D scene)
            └──► dashboard.py               (Streamlit live web UI)
```

The system is built around a **publish-subscribe DataBus** (Observer pattern), decoupling perception from rendering — the same architecture used in embedded automotive systems (publish-subscribe on CAN bus). Each renderer can be started and stopped independently.

---

## Features

### Perception (`core/perception.py`)
- **Object detection** with YOLOv8n — 8 traffic-relevant COCO classes: people, bicycles, cars, motorcycles, buses, trucks, traffic lights, stop signs
- **Distance estimation** per object using the pin-hole camera formula: `d = (W_real × f) / W_pixels`
- **Relative speed tracking** — frame-to-frame spatial proximity matching with 6-frame rolling average
- **Lane detection** — full 7-step pipeline: HLS+Sobel masking → morphological close → bird's-eye warp → histogram → sliding window → cross-lane fallback → 7-frame smoothing
- **Traffic light color** — HSV analysis on bbox ROI for red/yellow/green LED state
- **Road surface classification** — brightness + texture variance analysis → dry asphalt / wet asphalt / gravel, with friction coefficient μ and grip class A/B/C
- **Fog / visibility estimation** — horizon contrast analysis (std deviation of grayscale) → visibility in meters

### Driving Logic (`core/logic.py`)
- **Strict priority chain**: Traffic light → Stop sign → Pedestrian → Vehicle
- **Braking decisions**: `strong` / `light` / `none` based on distance thresholds per object class
- **Lane change**: only triggered when the right lane is confirmed clear (no vehicle within 30m at lateral offset > 1.5m)
- **Safe default state**: resets to `speed: increase`, `brake: none` every frame — if no hazard is found, the system defaults to safe acceleration
- **Human-readable audit log**: every decision is logged with full reasoning

```
[1712345678.5] RISK:high | BRAKE:strong | SPEED:decrease | LANE:change_lane | REASON:car@6.5m | ROAD:dry_asphalt | MU:0.7 | GRIP:A | FOG:good_visibility | VIZ:500m
```

### Rendering

**2D Radar (`rendering/renderer_2d.py`)** — Pygame top-down view:
- Road geometry with dual yellow center line and dashed right lane line (from real lane detection data)
- Each object class rendered with unique color and real-world-proportional dimensions
- Ego vehicle changes color reactively (green / orange / red) based on braking state
- Road surface info overlay (μ, grip class, visibility)

**3D Scene (`rendering/renderer_3d.py`)** — OpenGL perspective view:
- Real-scale 3D cubes per object class (car: 1.1×0.7×2.2m, truck: 1.3×1.5×4.5m, ...)
- Lane lines positioned from real lane geometry data
- Traffic light: separate body + colored LED cube
- **Skid effect** (+5p bonus): lateral impulse on `brake=strong` onset, exponential damping over ~10 frames
- **Brake trail marks** (+5p bonus): accumulated black strips on road surface for both rear wheels

**Web Dashboard (`dashboard.py`)** — Streamlit live UI:
- 4 driving decision metrics (risk, braking, speed, lane) with color-coded icons
- 4 road condition metrics (surface, μ, grip class, visibility)
- Live detected objects table
- **Braking distance formulas** (+10p bonus): `d = v²/(2μg) + v×1.5s` with live values from detection, comparison table across grip classes
- Live log feed (last 40 lines)
- One-click launch buttons for all pipeline components (Play / 2D / 3D / Stop)

### Data Pipeline (`main.py`)
- Structured JSON export every 0.5s to `output/data.json` — consumed by all renderers via polling
- Observer pattern DataBus for programmatic subscription
- 30fps polling in renderers with max ~500ms latency to main pipeline

---

## Tech Stack

| Layer | Technology |
|---|---|
| Object detection | [YOLOv8n](https://github.com/ultralytics/ultralytics) (Ultralytics) |
| Computer vision | OpenCV (`opencv-contrib-python`) |
| 2D rendering | Pygame |
| 3D rendering | PyOpenGL |
| Web dashboard | Streamlit |
| Package management | [uv](https://github.com/astral-sh/uv) |

---

## Project Structure

```
ProveIT_2026v4/
├── core/
│   ├── perception.py    # YOLO, lane detection, road surface, fog estimation
│   └── logic.py         # driving decisions (priority chain, safe defaults)
├── rendering/
│   ├── renderer_2d.py   # Pygame top-down radar
│   └── renderer_3d.py   # OpenGL 3D scene + skid + brake trails
├── output/
│   ├── data.json        # live data bus (decisions, objects, road info)
│   └── system.log       # full audit trail
├── main.py              # main pipeline + DataBus observer
├── dashboard.py         # Streamlit web dashboard
└── video_test.mp4       # test input video
```

---

## Installation

```bash
# With uv (recommended)
uv sync

# Or with pip
pip install opencv-contrib-python pygame ultralytics streamlit PyOpenGL PyOpenGL_accelerate
```

`yolov8n.pt` is downloaded automatically on first run.

---

## Running

```bash
# Terminal 1 — main pipeline (cv2 window with HUD)
python main.py

# Terminal 2 — 2D radar
python rendering/renderer_2d.py

# Terminal 3 — 3D scene
python rendering/renderer_3d.py

# Terminal 4 — web dashboard → http://localhost:8501
python -m streamlit run dashboard.py
```

Or launch everything from the dashboard using the Play / 2D / 3D buttons.

---

## Key Design Decisions

**Why YOLOv8n and not a larger model?**
YOLOv8n processes a frame in ~30ms on CPU. Larger variants (s, m) would exceed real-time on hackathon hardware. Nano accuracy is sufficient at relevant driving distances (under 70m).

**Why pin-hole distance estimation without LiDAR?**
`d = (W_real × f) / W_pixel` — works well for front-facing objects. Error is ±15% at normal distances, which is within the safety margin built into braking thresholds (2× factor in safety checks).

**Why the Observer/DataBus pattern?**
Decouples perception from all rendering. Renderers have zero knowledge of the pipeline internals and can be started or killed independently. Same publish-subscribe model used in embedded automotive (CAN bus).

**Why is lane change gated?**
`change_lane` is only set when `right_lane_clear = True` — no vehicle with lateral offset > 1.5m within 30m on the right. Avoids triggering a lane change into occupied space, which is more dangerous than holding position.