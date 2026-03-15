# Voice Bridge Pro

离线语音助手引擎，支持 ASR 语音识别、TTS 语音合成、语音唤醒。支持多平台接入：Telegram、企业微信、钉钉、飞书、WhatsApp、QQ。

## 功能

- 🎤 **语音识别 (ASR)** - 基于 sherpa-onnx，支持中文、英文、日语、韩语、粤语
- 🔊 **语音合成 (TTS)** - 基于 Kokoro，支持多音色
- 🤖 **语音助手** - 支持唤醒词、时间查询、日期查询等命令
- 💬 **多平台支持** - Telegram、企业微信、钉钉、飞书、WhatsApp、QQ

## 使用方法

### 直接调用

```python
from main import handle_voice_message, handle_text_message

# 处理语音
result = handle_voice_message("path/to/audio.ogg")
print(result["text"])  # 回复文本
print(result["voice"])  # 回复语音文件路径

# 处理文本
result = handle_text_message("你好")
print(result["text"])
```

### HTTP API

```bash
# 健康检查
curl http://localhost:8000/health

# 处理语音
curl -X POST http://localhost:8000/voice/process \
  -H "Content-Type: application/json" \
  -d '{"audio_file": "path/to/audio.ogg"}'

# 处理文本
curl -X POST http://localhost:8000/text/process \
  -H "Content-Type: application/json" \
  -d '{"text": "你好"}'
```

### Webhook

各平台 Webhook 地址：`POST /webhook/{adapter_name}`

支持的 adapter_name：telegram, wecom, dingtalk, feishu, whatsapp, qq

## 配置

编辑 `config.yaml`：

```yaml
language: zh
voice: female
wake_word: "hey claw"
auto_voice_reply: true

# 启用适配器
adapters:
  telegram:
    enabled: true
    token: "YOUR_BOT_TOKEN"
```

## 模型下载

```bash
python scripts/download_models.py
```

## 命令

- `你好` / `hello` - 打招呼
- `时间` / `time` - 查询当前时间
- `日期` / `date` - 查询今天日期
- `帮助` / `help` - 显示帮助信息
- 说唤醒词 `hey claw` - 唤醒助手

## 依赖

- sherpa-onnx
- fastapi
- requests
- pyyaml
- pydub
- numpy
- soundfile
