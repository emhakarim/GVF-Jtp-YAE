"""
FastAPI Hybrid Web Server untuk Galileo Vacuum Fall Experiment
Menyediakan streaming video low-latency, endpoint WebSocket real-time,
dan kontrol aktuator ESP32 dengan backend komputasi 100 FPS native.
"""

import os
import sys
import time
import json
import base64
import asyncio
import threading
from typing import Set
import cv2
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Pastikan folder app/ masuk dalam path import
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from app.physics_engine import PhysicsEngine
from app.camera_worker import CameraWorker
from app.scene_detector import SceneDetector
from app.comm_manager import CommManager

app = FastAPI(title="Galileo Vacuum Fall Web Server")

# Mount folder assets statis (logo, dll)
assets_dir = os.path.join(current_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Inisialisasi Modul
physics = PhysicsEngine(height_meters=2.0, delta_h_meters=0.002)
detector = SceneDetector(buffer_size=120)
comm = CommManager()
camera = CameraWorker(camera_index=0, target_fps=100, width=640, height=480, detector=detector)

# Buffer frame global & status
latest_annotated_frame = camera.static_mock_canvas.copy()
latest_frame_lock = threading.Lock()
connected_websockets: Set[WebSocket] = set()
current_fps = 100.0
replay_cache = []
shutdown_timer_handle = None
loop: asyncio.AbstractEventLoop = None

def schedule_auto_shutdown():
    global shutdown_timer_handle, loop
    if len(connected_websockets) == 0 and loop is not None:
        try:
            if loop.is_running() and (shutdown_timer_handle is None or shutdown_timer_handle.cancelled()):
                shutdown_timer_handle = loop.call_later(25.0, execute_auto_shutdown)
                print("[SERVER] Browser ditutup. Server akan mati otomatis dalam 25 detik jika tidak dibuka kembali.")
        except Exception:
            pass

def cancel_auto_shutdown():
    global shutdown_timer_handle
    if shutdown_timer_handle is not None and not shutdown_timer_handle.cancelled():
        shutdown_timer_handle.cancel()
        shutdown_timer_handle = None
        print("[SERVER] Browser aktif terdeteksi. Auto-shutdown dibatalkan.")

def execute_auto_shutdown():
    if len(connected_websockets) == 0:
        print("[SERVER] Semua browser telah ditutup. Mematikan server & kamera secara aman...")
        camera.stop()
        os._exit(0)

# ================= CALLBACK KAMERA & DETEKTOR =================
def on_display_frame(annotated: np.ndarray):
    global latest_annotated_frame
    with latest_frame_lock:
        latest_annotated_frame = annotated


def on_fps(fps: float):
    global current_fps
    current_fps = fps

def on_arrival(event_data: dict):
    t_arr = event_data["timestamp"]
    t_start = event_data["t_armed"]
    dt = t_arr - t_start
    g_val, g_err = physics.calculate_gravity_from_time(dt, delta_t_err=0.010)
    v_final = physics.theoretical_impact_velocity(g_val)
    dev = ((g_val - physics.G_STANDARD) / physics.G_STANDARD) * 100.0

    payload = {
        "type": "ARRIVAL_EVENT",
        "dt_ms": round(dt * 1000.0, 2),
        "g": round(g_val, 3),
        "g_err": round(g_err, 2),
        "v_impact": round(v_final, 2),
        "deviation_pct": round(dev, 2),
        "mode": event_data["target_mode"]
    }
    broadcast_json(payload)

def on_motion(motion_pct: float):
    payload = {
        "type": "MOTION_TELEMETRY",
        "timestamp": time.time(),
        "motion_pct": round(motion_pct, 2),
        "fps": round(current_fps, 1)
    }
    broadcast_json(payload)

def on_replay_ready(frames_list: list):
    # Offload encoding 120 frame ke worker thread agar thread kamera tidak tertahan
    threading.Thread(target=_process_replay_frames, args=(frames_list,), daemon=True).start()

def _process_replay_frames(frames_list: list):
    global replay_cache
    cache = []
    t_arm = detector.armed_timestamp if detector is not None else 0.0
    for item in frames_list:
        frame_img, t_stamp, idx = item
        small = cv2.resize(frame_img, (640, 480))
        _, buf = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 65])
        b64_str = base64.b64encode(buf).decode('utf-8')
        dt_rel = (t_stamp - t_arm) * 1000.0 if t_arm > 0 else 0.0
        cache.append({"b64": b64_str, "t": t_stamp, "dt_ms": round(dt_rel, 1), "idx": idx})
    replay_cache = cache
    broadcast_json({"type": "SLOWMO_READY", "total_frames": len(replay_cache)})

def broadcast_json(data: dict):
    global loop
    if not connected_websockets or loop is None:
        return
    msg = json.dumps(data)
    try:
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_async(msg), loop)
    except Exception:
        pass

async def broadcast_async(msg: str):
    disconnected = set()
    for ws in connected_websockets:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        connected_websockets.discard(ws)

# Sambungkan direct callback (FastAPI berjalan tanpa QCoreApplication event loop)
camera.display_callback = on_display_frame
camera.fps_callback = on_fps
camera.status_callback = lambda is_hw, msg: broadcast_json({
    "type": "CAMERA_STATUS",
    "is_hw": is_hw,
    "msg": msg
})

detector.arrival_callback = on_arrival
detector.motion_callback = on_motion
detector.slowmo_callback = on_replay_ready




# ================= ENDPOINT HTTP & STREAMING =================
@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    camera.start()

@app.on_event("shutdown")
async def shutdown_event():
    camera.stop()

@app.get("/")
def get_index():
    index_path = os.path.join(current_dir, "web", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Web dashboard index.html belum ditemukan.</h3>")

def generate_mjpeg():
    """Generator frame MJPEG untuk live view video pada browser."""
    try:
        while True:
            frame_to_stream = None
            with latest_frame_lock:
                if latest_annotated_frame is not None:
                    frame_to_stream = latest_annotated_frame

            if frame_to_stream is not None:
                # Encoding dilakukan di luar lock agar tidak memblokir thread akuisisi kamera
                display_frame = frame_to_stream if (frame_to_stream.shape[1] == 640 and frame_to_stream.shape[0] == 480) else cv2.resize(frame_to_stream, (640, 480))
                ret, jpeg = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    frame_bytes = jpeg.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' +
                           frame_bytes + b'\r\n')
            time.sleep(0.025) # ~40 FPS stream display
    except GeneratorExit:
        pass
    except Exception:
        pass

@app.get("/video_feed")
def video_feed():
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Connection": "close"
    }
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers=headers
    )

@app.get("/api/replay_frames")
def get_replay_frames():
    return JSONResponse(replay_cache)

# ================= WEBSOCKET KENDALI & TELEMETRI =================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_websockets.add(ws)
    cancel_auto_shutdown()
    
    # Kirim status awal
    ports = comm.list_serial_ports()
    cams = CameraWorker.list_available_cameras()
    active_cam = -1 if camera.is_mock else camera.camera_index
    await ws.send_text(json.dumps({
        "type": "INIT_STATE",
        "ports": ports,
        "cameras": [{"index": c[0], "label": c[1]} for c in cams],
        "active_camera": active_cam,
        "serial_connected": comm.is_serial_connected,
        "fps": current_fps
    }))

    try:
        while True:
            text = await ws.receive_text()
            data = json.loads(text)
            cmd = data.get("cmd")

            if cmd == "SWITCH_CAMERA":
                cam_idx = int(data.get("index", 0))
                camera.switch_camera(cam_idx)
                await ws.send_text(json.dumps({"type": "STATUS_LOG", "msg": f"Kamera dialihkan ke index {cam_idx}"}))

            elif cmd == "GET_CAMERAS":
                cams = CameraWorker.list_available_cameras()
                await ws.send_text(json.dumps({
                    "type": "CAMERAS_LIST",
                    "cameras": [{"index": c[0], "label": c[1]} for c in cams]
                }))

            elif cmd == "DROP_FEATHER":
                t_trig = time.perf_counter()
                detector.arm_detection(target_mode="FEATHER", t_trigger=t_trig)
                comm.trigger_drop_feather()
                if camera.is_mock: camera.trigger_mock_drop("FEATHER")
                await ws.send_text(json.dumps({"type": "STATUS_LOG", "msg": "Drop BULU diinstruksikan"}))

            elif cmd == "DROP_BALL":
                t_trig = time.perf_counter()
                detector.arm_detection(target_mode="BALL", t_trigger=t_trig)
                comm.trigger_drop_ball()
                if camera.is_mock: camera.trigger_mock_drop("BALL")
                await ws.send_text(json.dumps({"type": "STATUS_LOG", "msg": "Drop BOLA BESI diinstruksikan"}))

            elif cmd == "DROP_BOTH":
                t_trig = time.perf_counter()
                detector.arm_detection(target_mode="BOTH", t_trigger=t_trig)
                comm.trigger_drop_both()
                if camera.is_mock: camera.trigger_mock_drop("BOTH")
                await ws.send_text(json.dumps({"type": "STATUS_LOG", "msg": "Drop SIMULTAN (Bulu + Bola) diinstruksikan"}))

            elif cmd == "RESET":
                detector.reset()
                comm.reset_servos()
                await ws.send_text(json.dumps({"type": "STATUS_LOG", "msg": "Aktuator & Detektor direset"}))

            elif cmd == "CONNECT_SERIAL":
                port = data.get("port")
                ok = comm.connect_serial(port, 115200)
                await ws.send_text(json.dumps({
                    "type": "SERIAL_STATUS",
                    "connected": ok,
                    "msg": f"Serial {port} {'Terhubung' if ok else 'Gagal'}"
                }))

            elif cmd == "GET_PORTS":
                ports = comm.list_serial_ports()
                await ws.send_text(json.dumps({"type": "PORTS_LIST", "ports": ports}))

            elif cmd == "SET_THRESH":
                th = float(data.get("val", 4.0))
                detector.set_threshold(th)

    except (WebSocketDisconnect, Exception):
        connected_websockets.discard(ws)
        schedule_auto_shutdown()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=False)
