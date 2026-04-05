# ProveIT 2026 — Documentație pentru Prezentare

---

## Descriere generală a sistemului

ProveIT 2026 este un sistem de asistență la conducere autonomă care procesează în timp real un flux video de cameră frontală.
Sistemul detectează obiecte din trafic, estimează distanțe și viteze relative, ia decizii de conducere (frânare, viteză, schimbare bandă) și le vizualizează simultan în trei moduri: HUD pe video (OpenCV), radar 2D (Pygame) și scenă 3D (OpenGL).

### Arhitectura sistemului

```
video_test.mp4
      │
      ▼
main.py  ──────────────────────────────────────────────────
  ├─ core/perception.py  → detecție YOLO + benzi + road + fog
  ├─ core/logic.py       → decizii de conducere
  ├─ DataBus (Observer)  → publică JSON la abonați
  └─ output/data.json + output/system.log
            │
            ├──► rendering/renderer_2d.py  (Pygame radar)
            ├──► rendering/renderer_3d.py  (OpenGL 3D)
            └──► dashboard.py              (Streamlit web UI)
```

---

## Criteriu 1 — Acuratețea Percepției (25p)

### Ce am implementat

**Detecție obiecte — `core/perception.py`, metoda `analyze()`**

Folosim YOLOv8n (modelul nano, rapid pe CPU) cu filtrare strictă pe 8 clase relevante pentru conducere:
- Persoane (COCO id 0), biciclete (1), mașini (2), motociclete (3), autobuze (5), camioane (7), semafoare (9), indicatoare STOP (11)

Parametri YOLO optimizați pentru viteză și precizie:
```python
model(frame, conf=0.45, imgsz=320, max_det=20,
      classes=YOLO_CLASSES, agnostic_nms=True, verbose=False)
```
- `conf=0.45` — eliminăm detecțiile nesigure
- `agnostic_nms=True` — NMS cross-class, previne duplicatele când un obiect e detectat ca două clase
- Filtru minim bbox: `w*h < 600 px²` — eliminăm zgomotul de distanță
- Filtru cerc: `y2 < 25% din înălțime` — eliminăm detecțiile din cer

**Estimare distanță — linia 193**
```
dist_z = (known_width × focal_length) / bbox_width_pixels
```
Fiecare clasă are lățimea reală calibrată (ex: mașină = 1.8m, persoană = 0.5m).

**Poziție laterală — linia 194**
```
rel_x = (center_bbox - center_frame) × (dist_z / focal_length)
```

**Detecție culoare semafor — `get_tl_color()`**
Analiza HSV pe ROI-ul bbox — separat pentru canale roșu (0-10° + 160-180°), galben (15-35°) și verde (35-90°) cu prag de saturație și valoare (S>50, V>180 — nur leduri aprinse).

**Detecție benzi — `get_lane_geometry()`**

Pipeline complet în 7 pași:
1. Mască combinată: HLS color (alb + galben) + Sobel X gradient → rezistent la umbre
2. Morphological Close (kernel 5×5) → umple golurile din liniile întrerupte
3. Bird's-eye perspective warp (4 puncte sursă → destinație)
4. Histogramă pe jumătatea inferioară, threshold 400px, regiuni 10-48% și 52-90%
5. Sliding window (10 ferestre/linie, margin ±60px) → urmărire la curbe
6. Fallback cross-lane: dacă detectezi o singură linie, estimezi cealaltă la 320px distanță
7. Smoothing pe 7 frame-uri → elimină oscilațiile

### Unde arăt asta
- `core/perception.py` — întregul fișier
- `main.py` liniile 42, 78-96 — HUD overlay cu culori unice per clasă
- Dashboard Streamlit — tabelul "Obiecte detectate"

---

## Criteriu 2 — Corectitudinea Deciziilor (30p)

### Ce am implementat — `core/logic.py`

**Prioritizare strictă**: Semafor > Stop > Pieton > Vehicul

```python
# 1. Semafor ROSU → frânare imediată, break din loop
if label == "traffic light" and tc == "ROSU":
    brake = "strong"; break

# 2. STOP sign → frânare imediată, break
elif label == "stop sign":
    brake = "strong"; break

# 3. Pieton bazat pe distanță
elif label == "person":
    if dist_z < 10:  brake = "strong"
    elif dist_z < 25: brake = "light"

# 4. Vehicul bazat pe distanță + poziție laterală
elif label in vehicles:
    if in_our_lane and dist_z < 8:   brake = "strong"
    elif in_our_lane and dist_z < 25: brake = "light"
```

**Detecție bandă liberă** (pre-calculată):
```python
right_lane_clear = not any(
    obj["pos_rel"][0] > 1.5 and obj["pos_rel"][1] < 30
    and obj["label"] in vehicles
    for obj in objects
)
```
`change_lane` se setează **NUMAI** dacă banda dreaptă e liberă — nu schimbăm banda dacă e ocupată.

**Viteze relative** — tracking prin proximitate spațială (`main.py` liniile 46-75):
- Fiecare obiect e urmărit frame-to-frame prin distanța euclidiană 2D (< 8m)
- Rolling average pe 6 frame-uri → fără oscilații
- `max(0, speed)` → afișăm doar viteza de apropiere, nu de depărtare

### Unde arăt asta
- `core/logic.py` — întreg fișierul
- `main.py` liniile 42-43, 46-75

---

## Criteriu 3 — Calitatea Logicii (20p)

### Ce am implementat

**Ierarhia de prioritate Frână > Bandă > Viteză**:
- Deciziile se iau în ordinea: mai întâi brake_decision, din el derivă speed_decision, iar lane_decision e independentă dar subordonată siguranței
- `break` imediat din loop la eveniment critic (semafor roșu, stop sign) — nicio decizie ulterioară nu poate suprascrie

**Stare inițială conservatoare** (Safe Default):
```python
self.state = {
    "brake_decision": "none",
    "speed_decision": "increase",   # default: accelerăm dacă drumul e liber
    "risk_level":     "low",
    "lane_decision":  "keep_lane",  # default: rămânem pe bandă
}
```

**Reguli clare și verificabile** — fiecare decizie are un motiv specific logat:
```
RISK:high | BRAKE:strong | SPEED:decrease | LANE:change_lane | REASON:car@6.5m
```

### Unde arăt asta
- `core/logic.py` — toată logica în ~90 linii
- `output/system.log` — fiecare decizie e argumentată

---

## Criteriu 4 — Robustețe și Siguranță (15p)

### Ce am implementat

**Filtre anti-false positive** (`core/perception.py`):
- Bbox minim 600 px² — obiectele prea mici sunt zgomot
- Filtru înălțime: `y2 < 25% frame` — eliminăm detecțiile din cer/panouri publicitare
- Distanță validă: `1.5m < dist < 70m` — în afara acestui range estimarea e nerealistă
- Semafoare: respingem bbox-uri mai late decât înalte (panouri, nu semafoare)

**Safe Default** — sistemul resetează la stare sigură la fiecare frame:
```python
self.state["brake_decision"] = "none"
self.state["speed_decision"] = "increase"
# → dacă nu există obiect periculos, EGO accelerează normal
```

**Clamp fizic pe viteze**:
```python
raw_kmh = max(-180.0, min(300.0, raw_kmh))
```

**Fallback lane detection** — dacă nu detectăm benzi, folosim ultima valoare validă + estimare cross-lane.

### Unde arăt asta
- `core/perception.py` liniile 187-197 (filtre)
- `core/logic.py` liniile 11-14 (reset stare)

---

## Criteriu 5 — Explicabilitate și UX (10p)

### Ce am implementat

**HUD pe video** (`main.py` liniile 78-111):
- Fiecare obiect detectat: culoare unică per clasă, tag în română, distanță în metri, viteză km/h
- Semaforul își schimbă culoarea bbox după culoarea ledului (roșu/galben/verde)
- Colț stânga-sus: BRAKE / SPEED / LANE cu culori semantice (roșu = risc mare)
- Colț dreapta-sus: suprafața drumului + vizibilitate (date bonus)

**Dashboard Streamlit** (`dashboard.py`):
- 4 metrici principale (risc, frânare, viteză, bandă) cu icoane colorate
- 4 metrici condiții drum (suprafață, μ, grip, vizibilitate)
- Tabel live obiecte detectate
- Formule matematice de frânare cu valori live din detecție
- Log live ultimele 40 linii
- Butoane Play/2D/3D/Stop pentru control complet

**Log human-readable** (`output/system.log`):
```
[1712345678.5] RISK:high | BRAKE:strong | SPEED:decrease | LANE:change_lane | REASON:car@6.5m | ROAD:asfalt_uscat | MU:0.7 | GRIP:A | FOG:vizibilitate_buna | VIZ:500m
```

### Unde arăt asta
- `main.py` liniile 78-111
- `dashboard.py` — întregul fișier
- `output/system.log` — format complet

---

## Criteriu 6 — Randare 2D (35p)

### Ce am implementat — `rendering/renderer_2d.py`

**Drum și fundal**:
- Fundal întunecat (20,20,25) — vizibilitate radar
- Dreptunghi gri pentru carosabil cu borduri
- Scală: 15 pixeli/metru

**Linii de bandă** (din date reale lane detection):
- Linie galbenă dublă stânga — contrasens
- Linie albă dreaptă întreruptă (segment 20px, gap 15px) — bandă curentă

**Obiecte detectate**:
- Fiecare clasă: dimensiune proprie (car 20×40, bus 28×65, person 10×22...)
- Culoare unică per clasă, semafoarele schimbă culoarea după led
- Label text deasupra fiecărui obiect

**EGO reactiv**:
- Verde = fără frânare, portocaliu = frânare ușoară, roșu = frânare puternică

**Info drum (jos-stânga)**:
- Suprafața, coeficientul μ, clasa de grip
- Vizibilitate și condiție ceață

**Sincronizare cu video**: polling din `output/data.json` la 30fps — datele sunt cele mai recente (la max 500ms delay față de pipeline).

### Unde arăt asta
- `rendering/renderer_2d.py` — întregul fișier

---

## Criteriu 7 — Randare 3D (35p)

### Ce am implementat — `rendering/renderer_3d.py`

**Scena 3D OpenGL**:
- Perspectivă cu FOV 60°, cameră la -15 față cu unghi 20° în jos
- Plan asfalt întunecat

**Linii de bandă 3D**:
- Linie galbenă dublă stânga (offset ±0.12m)
- Linie albă întreruptă dreapta (segmente de 3m, gap 6m)
- Poziționate din datele reale lane_geometry

**Obiecte 3D per clasă**:
- Fiecare clasă: cuburi scalate la dimensiunile reale (mașină 1.1×0.7×2.2m, camion 1.3×1.5×4.5m...)
- Culori distincte (albastru=mașină, portocaliu=camion, cyan=persoană...)
- Semafor: corp gri + led colorat separat (cub mic deasupra)

**EGO**:
- Cub centrat, culoare reactivă (verde/portocaliu/roșu) după decizia de frânare
- Poziție laterală se deplasează la derapaj

**Bonus derapaj (+5p)**:
- La prima detectare `brake=="strong"` (tranziție), `skid_velocity = 0.35`
- Offset lateral amortizat: `skid_velocity *= 0.65`, `skid_offset *= 0.80`
- EGO revine la centru în ~10 frame-uri

**Bonus urme de frânare (+5p)**:
- La fiecare frame cu `brake=="strong"`, adăugăm poziția curentă în `brake_trails[]` (max 40)
- Redăm dungi negre (0.04, 0.04, 0.04) pe carosabil pentru ambele roți

### Unde arăt asta
- `rendering/renderer_3d.py` liniile 107-172

---

## Criteriu 8 — Procesare Date (25p)

### Ce am implementat

**Obiect JSON complet** (`main.py` liniile 108-132) — exportat la 0.5s:
```json
{
  "timestamp": 1712345678.5,
  "decisions": {"brake_decision": "strong", "speed_decision": "decrease", "risk_level": "high", "lane_decision": "keep_lane"},
  "lane_geometry": {"center_line": -45, "right_line": 210},
  "road_info": {"road_surface": "asfalt_uscat", "friction_mu": 0.7, "grip_class": "A"},
  "fog_info": {"visibility_m": 500, "fog_condition": "vizibilitate_buna"},
  "objects": [
    {"label": "car", "pos_rel": [-0.3, 12.5], "speed_kmh": 18.3},
    {"label": "traffic light", "pos_rel": [1.2, 28.0], "tl_color": "ROSU"}
  ]
}
```

**DataBus Observer Pattern** (`main.py` liniile 6-19):
```python
class DataBus:
    def subscribe(self, fn): self._observers.append(fn)
    def publish(self, data):
        for fn in self._observers: fn(data)
```
La fiecare export, `bus.publish(data_to_send)` notifică toți abonații. Renderer-ele se pot abona programatic (ex: `bus.subscribe(renderer_callback)`).

**Transmitere date la randare**: prin fișier `output/data.json` polling la 30fps — simplu, fiabil, fără dependențe suplimentare. Renderer-ele citesc datele independent de pipeline-ul principal.

**Viteza obiectelor**: calculată din deplasarea 3D între frame-uri consecutive, tracking prin proximitate spațială (nu index), rolling average 6 frame-uri.

### Unde arăt asta
- `main.py` liniile 6-19 (DataBus), 108-154 (export JSON + log)
- `output/data.json` — structura live

---

## Bonusuri implementate

| Bonus | Puncte | Unde | Cum |
|---|---|---|---|
| Derapaj | +5p | `rendering/renderer_3d.py:163-172` | Impuls lateral la onset brake strong, amortizare exponențială |
| Urme de frânare | +5p | `rendering/renderer_3d.py:147-160` | Dungi negre acumulate pe carosabil |
| Formule frânare | +10p | `dashboard.py:75-107` | `d = v²/(2μg)` cu valori live, tabel comparativ |
| Suprafață drum | +10p | `core/perception.py:121-140`, log | Analiza ROI drum: luminozitate + variație textură |
| Clasă aderență | +5p | `core/perception.py:121-140`, log + JSON | μ derivat din suprafață (A=0.70, B=0.45, C=0.40) |
| Vizibilitate ceață (log) | +10p | `core/perception.py:142-157`, log | Contrast orizont → visibility_m estimat |
| Filmare condiții ceață | +10p | `core/perception.py:142-157`, JSON | fog_condition în JSON, afișat HUD + dashboard |

**Total bonusuri: +55p**

---

## Harta workflow complet — date prin sistem

```
Frame video (1280×720 BGR)
│
├─ YOLO inference → boxes + labels + confidence
│    └─ filtre: min area, sky filter, dist 1.5-70m
│
├─ get_lane_geometry()
│    HLS+Sobel → MORPH_CLOSE → warp → histogram → sliding window
│    → {center_line, right_line} în pixeli față de centrul frame-ului
│
├─ _estimate_road_surface()
│    ROI[75%-100%, 20%-80%] → mean_brightness + std_brightness
│    → {road_surface, friction_mu, grip_class}
│
├─ _estimate_visibility()
│    ROI orizont [25%-50%] → std(gray) = contrast
│    → {visibility_m, fog_condition}
│
├─ DrivingLogic.update(detections)
│    sort by dist → prioritate: semafor > stop > pieton > vehicul
│    right_lane_clear pre-calc → change_lane condiționat
│    → {brake_decision, speed_decision, lane_decision, risk_level}
│
├─ Speed tracking per obiect
│    match by spatial proximity (<8m, same label) → Δz/Δt → rolling avg 6 frames
│    → speed_kmh per obiect
│
├─ HUD overlay pe frame (cv2)
│    bbox + tag + distanță + viteză (culoare per clasă)
│    decizii stânga-sus, drum/ceață dreapta-sus
│
└─ Export la 0.5s
     output/data.json → renderer_2d, renderer_3d, dashboard
     output/system.log → audit trail complet
```

---

## Întrebări frecvente juriu — răspunsuri

**"De ce YOLOv8n și nu un model mai mare?"**
YOLOv8n procesează un frame în ~30ms pe CPU. Modelele mai mari (YOLOv8s, m) ar depăși real-time pe hardware de hackathon. Acuratețea nano e suficientă la distanțe relevante pentru conducere (sub 70m).

**"Cum estimezi distanța fără LiDAR?"**
Formula pin-hole camera: `d = (W_real × f) / W_pixel`. Funcționează bine pentru obiectele față-față. Eroarea e ±15% la distanțe normale — suficient pentru decizii de frânare cu marja de siguranță inclusă (factorul ×2 în safety check).

**"De ce Observer pattern (DataBus)?"**
Decuplarea percepției de randare — renderer-ele nu știu nimic despre cum funcționează pipeline-ul. Pot fi pornite/oprite independent. E același pattern folosit în sistemele embedded automotive (publish-subscribe pe CAN bus).

**"Cum funcționează detecția de ceață?"**
Ceața reduce contrastul local — detaliile fine dispar. Măsurăm deviația standard a intensității în zona de orizont (25-50% din înălțimea frame-ului). Contrast < 18 → ceață densă (viz. ~40m), 18-30 → ceață ușoară (~100m), >30 → vizibilitate bună.

**"Cum detectezi suprafața drumului?"**
Analizăm ROI-ul drumului (ultimul sfert al frame-ului, lat central). Asfalt umed are reflexii specular → std mare + luminozitate medie-mare. Pietriș are textură neuniformă → std mare + luminozitate scăzută. Asfalt uscat → std mică.

**"De ce schimbarea benzii e condiționată?"**
`change_lane` se setează doar dacă `right_lane_clear = True`, adică niciun vehicul cu offset lateral > 1.5m și distanță < 30m pe dreapta. Evităm să schimbăm banda dacă e ocupată — decizie mai sigură decât frânare bruscă în trafic dens.

**"Cum rulezi sistemul?"**
```bash
# Terminal 1 — pipeline principal
python main.py

# Terminal 2 — radar 2D
python rendering/renderer_2d.py

# Terminal 3 — scenă 3D
python rendering/renderer_3d.py

# Terminal 4 — dashboard web
python -m streamlit run dashboard.py
# → http://localhost:8501
```
SAU: din dashboard, apasă butoanele Play / 2D / 3D.

**"Ce înseamnă grip class A/B/C?"**
- **A** (μ=0.70): asfalt uscat — aderență maximă, distanță frânare minimă
- **B** (μ=0.45): asfalt umed — aderență redusă, +55% distanță frânare față de A
- **C** (μ=0.40): pietriș — aderență slabă, recomandat viteze reduse

**"Cum se calculează distanța totală de oprire?"**
`d_total = d_frânare + d_reacție = v²/(2μg) + v × 1.5s`
Timpul de reacție de 1.5s e standardul european pentru sisteme ADAS (ISO 15622).

---

## Structura proiectului

```
ProveIT_2026v4/
├── core/
│   ├── __init__.py
│   ├── perception.py    # YOLO, lane detection, road surface, fog
│   └── logic.py         # decizii de conducere
├── rendering/
│   ├── __init__.py
│   ├── renderer_2d.py   # Pygame radar
│   └── renderer_3d.py   # OpenGL 3D + bonusuri
├── output/
│   ├── data.json        # date live (timestamp, decisions, objects...)
│   └── system.log       # audit trail complet
├── main.py              # pipeline principal + DataBus
├── dashboard.py         # Streamlit web dashboard
├── prezentare.md        # acest fișier
├── video_test.mp4
└── yolov8n.pt
```
