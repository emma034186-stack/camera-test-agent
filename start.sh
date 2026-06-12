#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export ANTHROPIC_API_KEY="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"

echo "Camera Test Agent 啟動中..."
echo "開啟瀏覽器：http://127.0.0.1:5001"
echo "按 Ctrl+C 停止"
echo ""

while true; do
    python app.py
    echo "[$(date '+%H:%M:%S')] Server 停止，3 秒後重啟..."
    sleep 3
done
