from flask import Flask, render_template, jsonify, send_from_directory, Response
from datetime import datetime
from dotenv import load_dotenv
import json
import os
import cv2
import threading
import time
from camera import process_frame
from agent import analyze

load_dotenv()

app = Flask(__name__)
REPORT_FILE = "reports.json"


# ── Continuous camera stream ──────────────────────────────────────────────────

class CameraStream:
    def __init__(self, index: int = 0):
        self.index = index
        self.cap = None
        self.frame = None
        self.frame_lock = threading.Lock()
        self.cap_lock = threading.Lock()
        self.running = False
        self._thread = None

    def start(self):
        if self.running:
            return
        with self.cap_lock:
            self.cap = cv2.VideoCapture(self.index)
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        with self.cap_lock:
            if self.cap:
                self.cap.release()
                self.cap = None
        with self.frame_lock:
            self.frame = None

    def _loop(self):
        while self.running:
            try:
                with self.cap_lock:
                    if self.cap is None:
                        break
                    ret, frame = self.cap.read()
                if ret:
                    with self.frame_lock:
                        self.frame = frame
                else:
                    time.sleep(0.05)
            except Exception:
                time.sleep(0.1)

    def get_frame(self):
        with self.frame_lock:
            return self.frame.copy() if self.frame is not None else None

    def jpeg_generator(self):
        import numpy as np
        offline = np.full((360, 640, 3), (17, 24, 39), dtype=np.uint8)
        cv2.putText(offline, "Camera Offline", (185, 190),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (75, 85, 99), 2)
        _, offline_buf = cv2.imencode(".jpg", offline)
        offline_bytes = offline_buf.tobytes()

        while True:
            try:
                frame = self.get_frame()
                data = (
                    cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])[1].tobytes()
                    if frame is not None and self.running
                    else offline_bytes
                )
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
                time.sleep(1 / 30)
            except GeneratorExit:
                return
            except Exception:
                time.sleep(0.1)


stream = CameraStream()


# ── Recorder ──────────────────────────────────────────────────────────────────

class Recorder:
    def __init__(self, cam: CameraStream):
        self.cam = cam
        self.recording = False
        self._writer = None
        self._path = None
        self._thread = None
        self._start_time = None

    def start(self):
        if self.recording:
            return None
        frame = self.cam.get_frame()
        if frame is None:
            return None
        os.makedirs("videos", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = f"videos/rec_{timestamp}.mp4"
        h, w = frame.shape[:2]
        self._writer = cv2.VideoWriter(
            self._path, cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (w, h)
        )
        self.recording = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 開始錄影 → {self._path}")
        return self._path

    def stop(self):
        if not self.recording:
            return None
        self.recording = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._writer:
            self._writer.release()
            self._writer = None
        path = self._path
        duration = round(time.time() - self._start_time, 1)
        size_kb = round(os.path.getsize(path) / 1024, 1) if path and os.path.exists(path) else 0
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏹  錄影停止 → {path}  ({duration}s, {size_kb} KB)")
        self._path = None
        return {"path": path, "duration": duration, "size_kb": size_kb}

    def elapsed(self):
        if not self.recording or not self._start_time:
            return 0
        return round(time.time() - self._start_time, 1)

    def _loop(self):
        while self.recording:
            frame = self.cam.get_frame()
            if frame is not None and self._writer:
                self._writer.write(frame)
            time.sleep(1 / 30)


recorder = Recorder(stream)


# ── Report helpers ────────────────────────────────────────────────────────────

MAX_RECORDS = 20


def _delete_files(record: dict):
    for key in ("image_path", "video_path"):
        path = record.get("camera", {}).get(key)
        if path and os.path.exists(path):
            os.remove(path)


def save_report(results, report, cost):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "camera": {
            "opened": results["camera_opened"],
            "frame_captured": results["frame_captured"],
            "resolution": results["resolution"],
            "brightness": results["brightness"],
            "image_path": results["image_path"],
            "video_path": results["video_path"],
            "errors": results["errors"],
        },
        "ai_report": report,
        "cost": cost,
    }

    all_reports = []
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            all_reports = json.load(f)

    all_reports.append("---")
    all_reports.append(entry)

    # 取出所有 dict 記錄，超過上限就刪最舊的
    records = [x for x in all_reports if isinstance(x, dict)]
    while len(records) > MAX_RECORDS:
        oldest = records.pop(0)
        _delete_files(oldest)

    # 重建含分隔線的完整列表
    rebuilt = []
    for r in records:
        rebuilt.append("---")
        rebuilt.append(r)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(rebuilt, f, ensure_ascii=False, indent=2)

    return entry


def load_reports():
    if not os.path.exists(REPORT_FILE):
        return []
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    reports = [x for x in data if isinstance(x, dict)]
    reports.reverse()
    return reports


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video-feed")
def video_feed():
    return Response(
        stream.jpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/camera/open", methods=["POST"])
def camera_open():
    if not stream.running:
        stream.start()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 攝影機已開啟")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  攝影機已經是開啟狀態")
    return jsonify({"status": "open"})


@app.route("/api/camera/close", methods=["POST"])
def camera_close():
    stream.stop()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏹  攝影機已關閉")
    return jsonify({"status": "closed"})


@app.route("/api/camera/status")
def camera_status():
    return jsonify({"open": stream.running})


@app.route("/api/record/start", methods=["POST"])
def record_start():
    path = recorder.start()
    if path is None:
        return jsonify({"error": "攝影機未開啟或已在錄影"}), 400
    return jsonify({"status": "recording", "path": path})


@app.route("/api/record/stop", methods=["POST"])
def record_stop():
    result = recorder.stop()
    if result is None:
        return jsonify({"error": "尚未開始錄影"}), 400
    filename = result["path"].split("/")[-1]
    return jsonify({
        "status": "saved",
        "filename": filename,
        "duration": result["duration"],
        "size_kb": result["size_kb"],
    })


@app.route("/api/record/status")
def record_status():
    return jsonify({"recording": recorder.recording, "elapsed": recorder.elapsed()})


@app.route("/api/take-photo", methods=["POST"])
def take_photo():
    frame = stream.get_frame()
    if frame is None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 拍照失敗：攝影機未開啟")
        return jsonify({"error": "攝影機未開啟"}), 400
    os.makedirs("images", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}.jpg"
    path = f"images/{filename}"
    cv2.imwrite(path, frame)
    size_kb = round(os.path.getsize(path) / 1024, 1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📸 拍照成功 → {path}  ({size_kb} KB)")
    return jsonify({"filename": filename})


@app.route("/api/run-test", methods=["POST"])
def run_test():
    import traceback
    try:
        frame = stream.get_frame()
        if frame is None:
            return jsonify({"error": ["攝影機尚未就緒"]}), 500

        results = process_frame(frame)
        report, cost = analyze(results)
        entry = save_report(results, report, cost)
        return jsonify(entry)
    except Exception as e:
        err = traceback.format_exc()
        print(f"[run-test ERROR]\n{err}")
        return jsonify({"error": str(e), "detail": err}), 500


@app.route("/api/reports")
def get_reports():
    return jsonify(load_reports())


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory("images", filename)


@app.route("/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory("videos", filename)


if __name__ == "__main__":
    stream.start()
    app.run(debug=False, port=5001, threaded=True)
