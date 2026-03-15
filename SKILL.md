# Voice Bridge Pro (轻量版)

离线语音助手引擎（轻量版），使用 **Whisper + Piper**，模型总大小仅 **~160MB**。

## 特性

- 🎤 **语音识别 (ASR)** - Whisper base (74MB)，支持多语言
- 🔊 **语音合成 (TTS)** - Piper Neural TTS (25-60MB)，自然流畅
- 🤖 **语音助手** - 支持唤醒词、命令处理
- 💬 **多平台支持** - Telegram、企业微信、钉钉、飞书、WhatsApp、QQ
- 🚀 **轻量级** - 总模型大小仅 160MB，适合边缘设备

## 模型大小对比

| 组件 | 原方案 (sherpa-onnx) | 轻量版 (Whisper+Piper) | 节省 |
|------|---------------------|----------------------|------|
| ASR | ~1GB | 74MB (base) | **93%** |
| TTS | ~300MB | 25-60MB | **90%** |
| **总计** | **~1.3GB** | **~160MB** | **88%** |

## 使用方法

### 直接调用

```python
from main import handle_voice_message, handle_text_message

# 处理语音
result = handle_voice_message("path/to/audio.ogg", language="zh")
print(result["text"])  # 回复文本
print(result["voice"])  # 回复语音文件路径

# 处理文本
result = handle_text_message("你好", reply_with_voice=True)
print(result["text"])
```

### HTTP API

```bash
# 健康检查
curl http://localhost:8000/health

# 处理语音
curl -X POST http://localhost:8000/voice/process \
  -H "Content-Type: application/json" \
  -d '{"audio_file": "path/to/audio.ogg", "language": "zh"}'

# 处理文本
curl -X POST http://localhost:8000/text/process \
  -H "Content-Type: application/json" \
  -d '{"text": "你好", "reply_with_voice": true}'

# 语音识别 (ASR)
curl -X POST http://localhost:8000/asr \
  -H "Content-Type: application/json" \
  -d '{"audio_file": "test.wav", "language": "zh"}'

# 语音合成 (TTS)
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，我是语音助手", "voice": "zh_CN"}'
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

# Whisper 配置
whisper_model_size: base  # tiny/base/small

# Piper 配置
piper_language: zh_CN  # zh_CN/en_US/en_US_low

# 启用适配器
adapters:
  telegram:
    enabled: true
    token: "YOUR_BOT_TOKEN"
```

## 模型下载

```bash
# 下载全部模型（约 160MB）
python scripts/download_models.py all

# 仅下载中文 TTS（60MB）
python scripts/download_models.py piper_zh

# 仅下载英文 TTS（25MB）
python scripts/download_models.py piper_en

# Whisper 首次使用时自动下载（74MB）
```

## 支持的语言

### Whisper ASR
- 中文 (zh)
- 英文 (en)
- 日语 (ja)
- 韩语 (ko)
- 更多...

### Piper TTS
- 中文女声 (zh_CN) - 60MB
- 英文女声 (en_US) - 60MB
- 英文轻量版 (en_US_low) - 25MB

## 命令

- `你好` / `hello` - 打招呼
- `时间` / `time` - 查询当前时间
- `日期` / `date` - 查询今天日期
- `帮助` / `help` - 显示帮助信息
- 说唤醒词 `hey claw` - 唤醒助手

## 依赖

必需：
- openai-whisper
- fastapi
- uvicorn
- pydantic
- requests
- pyyaml
- pydub
- numpy
- soundfile

可选：
- piper-tts（用于语音合成功能）
- torch（用于加速 Whisper）

## 部署测试

运行测试脚本验证安装：

```bash
python test_skill.py
```

预期输出：8/8 测试通过

## 项目结构

```
voice-bridge-pro/
├── main.py                 # FastAPI 入口
├── skill.yaml              # ClawHub 配置
├── requirements.txt        # 依赖
├── config.yaml             # 配置文件
├── test_skill.py           # 测试脚本
├── voice/
│   ├── asr_whisper.py      # Whisper 语音识别
│   ├── tts_piper.py        # Piper 语音合成
│   └── audio_utils.py      # 音频处理
├── assistant/
│   └── voice_assistant.py  # 语音助手逻辑
├── adapters/               # 多平台适配器
└── scripts/
    └── download_models.py  # 模型下载
```

## 许可证

MIT
