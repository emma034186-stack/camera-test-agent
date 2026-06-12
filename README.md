# Camera Test Agent

使用 AI 自動分析攝影機狀態，並產生結構化測試報告。支援即時串流預覽、錄影、拍照與功能測試結果追蹤。

---

## 系統架構

```
camera-test-agent/
├── app.py           # Flask 主服務，含 CameraStream、Recorder、API 路由
├── camera.py        # 單幀處理（截圖、亮度計算、base64）
├── agent.py         # 呼叫 Claude AI 分析影像
├── main.py          # CLI 版本（錄影 + 拍照 + AI 分析）
├── start.sh         # 自動重啟啟動腳本
├── .env             # API Key 設定
├── requirements.txt
├── templates/
│   └── index.html   # Web UI
├── images/          # 截圖存放
├── videos/          # 錄影存放
└── reports.json     # 所有測試報告（累積追加，上限 20 筆）
```

### 執行流程（Web 模式）

```
python app.py
  │
  ├─► CameraStream（背景執行緒）
  │     持續從攝影機擷取幀，30fps
  │
  ├─► /video-feed
  │     MJPEG 串流 → 瀏覽器即時預覽
  │
  ├─► Start Test 按鈕
  │     抓當前幀 → process_frame() → Claude AI → 儲存 reports.json
  │
  ├─► 快門按鈕
  │     抓當前幀 → 存 images/photo_xxx.jpg
  │
  └─► 錄影按鈕
        Recorder 執行緒持續寫幀 → 停止時存 videos/rec_xxx.mp4
```

### 報告格式（reports.json）

```json
[
  "---",
  {
    "timestamp": "2026-06-12T08:30:00",
    "camera": {
      "opened": true,
      "frame_captured": true,
      "resolution": "1280x720",
      "brightness": 135.2,
      "image_path": "images/capture_20260612_083000.jpg",
      "video_path": null,
      "errors": []
    },
    "ai_report": {
      "passed": true,
      "summary": "攝像頭工作正常",
      "brightness": { "value": 135.2, "status": "正常", "comment": "..." },
      "image_quality": { "resolution": "良好", "clarity": "清晰", "noise": "低" },
      "issues": [],
      "suggestions": ["建議1"]
    },
    "cost": {
      "input_tokens": 1439,
      "output_tokens": 280,
      "total_usd": 0.0023
    }
  }
]
```

> 超過 20 筆時自動刪除最舊的照片與影片檔案。

---

## Web UI 功能

| 區域 | 功能 |
|------|------|
| Live Preview | 即時 MJPEG 串流（30fps） |
| Test Metrics | Status / Resolution / Brightness / Cost |
| AI Analysis | Summary、AI Issues、Suggestions |
| 功能測試結果 | 每個按鈕操作的 PASS / FAIL 驗證結果 |
| Start Test | 擷取當前幀 → AI 分析 → 儲存報告 |
| 開啟 / 關閉攝影機 | 控制 CameraStream，即時反映在預覽畫面 |
| 📸 快門 | 拍照並儲存，驗證存檔成功 |
| 🎥 錄影 | 開始 / 停止錄影，驗證 MP4 產出與檔案大小 |
| Test History | 所有報告列表，可開啟截圖與影片 |
| Test Checklist | 右側欄測試項目勾選，含進度條，狀態存於 localStorage |

---

## 測試項目對應按鈕

| 測試項目 | 對應操作 | 驗證方式 |
|----------|---------|---------|
| 攝影機開啟 / 關閉 | 開啟 / 關閉按鈕 | `/api/camera/status` 確認狀態 |
| 預覽畫面（Preview stream）| Start Test | 成功擷取幀並完成 AI 分析 |
| 拍照功能（存檔）| 📸 快門 | 確認 image 檔案存在 |
| 錄影功能（MP4 產出）| 🎥 錄影 | 確認 MP4 存在且大小 > 0 |

---

## 環境需求

- Python 3.10+
- Anthropic API Key（[申請連結](https://console.anthropic.com/)）
- macOS：需授權終端機存取攝影機

---

## 安裝

```bash
# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝套件
pip install -r requirements.txt
```

---

## 設定 API Key

編輯 `.env` 檔（**不要貼在終端機指令中，避免換行導致 key 損壞**）：

```
ANTHROPIC_API_KEY=sk-ant-你的金鑰
```

---

## 啟動方式

### Web UI（推薦）
```bash
cd /Users/catherine/Projects/camera-test-agent
source venv/bin/activate
python app.py
```
瀏覽器開啟：`http://127.0.0.1:5001`

### CLI（含錄影）
```bash
python main.py
```

---

## macOS 攝影機授權

首次執行若出現攝影機權限錯誤：

1. 打開「系統設定」
2. 隱私權與安全性 → 攝影機
3. 開啟 Terminal 的存取權限
4. 重新執行程式

---

## 注意事項

- Port `5001`（macOS AirPlay Receiver 佔用 5000）
- API Key 請存於 `.env`，不要直接貼在終端機（避免換行截斷）
- reports.json 上限 20 筆，超過自動刪除最舊的照片與影片

---

## 使用的 AI 模型

| 用途 | 模型 |
|------|------|
| 影像與數據分析 | claude-haiku-4-5 |
