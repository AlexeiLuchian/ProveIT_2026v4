import streamlit as st
import json, subprocess, time, pathlib

ROOT      = pathlib.Path(__file__).parent
DATA_JSON = ROOT / "output" / "data.json"
SYS_LOG   = ROOT / "output" / "system.log"

st.set_page_config(page_title="ProveIT 2026", layout="wide")
st.title("ProveIT 2026 - Dashboard")

# ── Butoane control ────────────────────────────────────────────────────────────
if "procs" not in st.session_state:
    st.session_state.procs = {}

c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("Start Pipeline", use_container_width=True):
        if st.session_state.procs.get("main", None) is None or \
           st.session_state.procs["main"].poll() is not None:
            st.session_state.procs["main"] = subprocess.Popen(
                ["python", str(ROOT / "main.py")], cwd=str(ROOT)
            )
with c2:
    if st.button("2D Radar", use_container_width=True):
        if st.session_state.procs.get("2d", None) is None or \
           st.session_state.procs["2d"].poll() is not None:
            st.session_state.procs["2d"] = subprocess.Popen(
                ["python", str(ROOT / "rendering" / "renderer_2d.py")], cwd=str(ROOT)
            )
with c3:
    if st.button("3D Scene", use_container_width=True):
        if st.session_state.procs.get("3d", None) is None or \
           st.session_state.procs["3d"].poll() is not None:
            st.session_state.procs["3d"] = subprocess.Popen(
                ["python", str(ROOT / "rendering" / "renderer_3d.py")], cwd=str(ROOT)
            )
with c4:
    if st.button("Stop All", use_container_width=True):
        for p in st.session_state.procs.values():
            try: p.terminate()
            except Exception: pass
        st.session_state.procs.clear()

active = [k for k, p in st.session_state.procs.items() if p.poll() is None]
if active:
    st.caption("Active: " + ", ".join(active))

st.divider()

# ── JSON + Log side by side ───────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("data.json")
    if DATA_JSON.exists():
        try:
            raw = DATA_JSON.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw)
            st.json(data)
        except Exception as e:
            st.error(str(e))
    else:
        st.info("No data yet.")

with right:
    st.subheader("system.log")
    if SYS_LOG.exists():
        lines = SYS_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]
        st.code("\n".join(lines), language="text")
    else:
        st.info("No log yet.")

# ── Auto-refresh ───────────────────────────────────────────────────────────────
time.sleep(0.5)
st.rerun()
