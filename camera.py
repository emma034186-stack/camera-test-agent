import cv2
import base64
import os
import time
from datetime import datetime

IMAGES_DIR = "images"
VIDEOS_DIR = "videos"

RESOLUTION_SPECS = {
    (1280, 720): "720p",
    (1920, 1080): "1080p",
    (3840, 2160): "4K",
}

FPS_SPECS = [(30, "30fps"), (60, "60fps")]
FPS_TOLERANCE = 2.0


def check_resolution_spec(w: int, h: int) -> str | None:
    return RESOLUTION_SPECS.get((w, h))


def check_fps_spec(fps: float) -> str | None:
    for target, label in FPS_SPECS:
        if abs(fps - target) <= FPS_TOLERANCE:
            return label
    return None


def process_frame(frame, fps: float = 0.0) -> dict:
    """給 CameraStream 使用：直接處理已有的幀，不重新開攝影機"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f"{IMAGES_DIR}/capture_{timestamp}.jpg"
    cv2.imwrite(image_path, frame)

    _, buffer = cv2.imencode(".jpg", frame)
    w, h = frame.shape[1], frame.shape[0]

    return {
        "camera_opened": True,
        "frame_captured": True,
        "resolution": f"{w}x{h}",
        "resolution_spec": check_resolution_spec(w, h),
        "fps": round(fps, 2),
        "fps_spec": check_fps_spec(fps),
        "brightness": round(float(cv2.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))[0]), 2),
        "image_path": image_path,
        "video_path": None,
        "image_base64": base64.b64encode(buffer).decode("utf-8"),
        "errors": [],
    }


def capture(camera_index: int = 0, video_duration: float = 3.0) -> dict:
    results = {
        "camera_opened": False,
        "frame_captured": False,
        "resolution": None,
        "resolution_spec": None,
        "fps": None,
        "fps_spec": None,
        "brightness": None,
        "image_path": None,
        "video_path": None,
        "image_base64": None,
        "errors": [],
    }

    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        results["errors"].append(f"無法開啟攝影機 (index={camera_index})")
        return results

    results["camera_opened"] = True
    time.sleep(0.5)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(fps * video_duration)

    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = f"{VIDEOS_DIR}/capture_{timestamp}.mp4"
    image_path = f"{IMAGES_DIR}/capture_{timestamp}.jpg"

    writer = cv2.VideoWriter(
        video_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    snapshot_frame = None
    snapshot_index = total_frames // 2

    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            results["errors"].append(f"第 {i} 幀擷取失敗")
            break
        writer.write(frame)
        if i == snapshot_index:
            snapshot_frame = frame

    writer.release()
    cap.release()

    if snapshot_frame is None:
        results["errors"].append("無法取得代表幀")
        return results

    results["frame_captured"] = True
    results["resolution"] = f"{width}x{height}"
    results["resolution_spec"] = check_resolution_spec(width, height)
    results["fps"] = round(fps, 2)
    results["fps_spec"] = check_fps_spec(fps)
    results["brightness"] = round(
        float(cv2.mean(cv2.cvtColor(snapshot_frame, cv2.COLOR_BGR2GRAY))[0]), 2
    )
    results["video_path"] = video_path

    cv2.imwrite(image_path, snapshot_frame)
    results["image_path"] = image_path

    _, buffer = cv2.imencode(".jpg", snapshot_frame)
    results["image_base64"] = base64.b64encode(buffer).decode("utf-8")

    return results
