import cv2
import base64
import os
import time
from datetime import datetime

IMAGES_DIR = "images"
VIDEOS_DIR = "videos"


def process_frame(frame) -> dict:
    """給 CameraStream 使用：直接處理已有的幀，不重新開攝影機"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = f"{IMAGES_DIR}/capture_{timestamp}.jpg"
    cv2.imwrite(image_path, frame)

    _, buffer = cv2.imencode(".jpg", frame)

    return {
        "camera_opened": True,
        "frame_captured": True,
        "resolution": f"{frame.shape[1]}x{frame.shape[0]}",
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
    results["brightness"] = round(
        float(cv2.mean(cv2.cvtColor(snapshot_frame, cv2.COLOR_BGR2GRAY))[0]), 2
    )
    results["video_path"] = video_path

    cv2.imwrite(image_path, snapshot_frame)
    results["image_path"] = image_path

    _, buffer = cv2.imencode(".jpg", snapshot_frame)
    results["image_base64"] = base64.b64encode(buffer).decode("utf-8")

    return results
