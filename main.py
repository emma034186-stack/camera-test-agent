import json
import os
from datetime import datetime
from camera import capture
from agent import analyze

REPORT_FILE = "reports.json"


def save_report(results: dict, report: dict, cost: dict) -> None:
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

    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            all_reports = json.load(f)
    else:
        all_reports = []

    all_reports.append("---")
    all_reports.append(entry)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)


def main():
    print("=== Camera Test Agent ===\n")

    print("[1/2] 錄影中（3 秒）+ 截取代表幀...")
    results = capture()

    if not results["camera_opened"]:
        print("錯誤：", results["errors"])
        return

    print(f"     解析度: {results['resolution']}, 亮度: {results['brightness']}")
    print(f"     照片: {results['image_path']}")
    print(f"     影片: {results['video_path']}")

    print("[2/2] 送給 AI 分析中...\n")
    report, cost = analyze(results)

    print("=== 測試報告 ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n花費：${cost['total_usd']} USD（input {cost['input_tokens']} / output {cost['output_tokens']} tokens）")

    save_report(results, report, cost)
    print(f"報告已追加至：{REPORT_FILE}")


if __name__ == "__main__":
    main()
