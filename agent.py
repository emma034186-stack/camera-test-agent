import json
import anthropic


def analyze(test_results: dict) -> dict:
    client = anthropic.Anthropic()

    status = f"""Camera 測試結果：
- 開啟成功: {test_results['camera_opened']}
- 擷取成功: {test_results['frame_captured']}
- 解析度: {test_results.get('resolution', 'N/A')}
- 亮度 (0-255): {test_results.get('brightness', 'N/A')}
- 錯誤: {test_results['errors'] or '無'}

請分析後以純 JSON 格式回傳（不要加 markdown code block），格式如下：
{{
  "passed": true or false,
  "summary": "一句話總結",
  "brightness": {{
    "value": 數字,
    "status": "正常/偏暗/過亮",
    "comment": "說明"
  }},
  "image_quality": {{
    "resolution": "評價",
    "clarity": "評價",
    "noise": "評價"
  }},
  "issues": ["問題1", "問題2"],
  "suggestions": ["建議1", "建議2"]
}}"""

    content = []

    if test_results.get("image_base64"):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": test_results["image_base64"],
            },
        })

    content.append({"type": "text", "text": status})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    analysis = json.loads(text.strip())

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_usd": round(input_tokens * 0.0000008 + output_tokens * 0.000004, 6),
    }

    return analysis, cost
