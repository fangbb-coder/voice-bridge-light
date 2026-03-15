# Voice Bridge

离线语音助手引擎，使用 Whisper + Piper，模型总大小约 160MB。

## 特性

- 🎤 **语音识别 (ASR)** - Whisper base (74MB)，支持多语言
- 🔊 **语音合成 (TTS)** - Piper Neural TTS (25-60MB)，自然流畅
- 🤖 **语音助手** - 支持唤醒词、命令处理
- 💬 **多平台支持** - Telegram、企业微信、钉钉、飞书、WhatsApp、QQ
- 🚀 **轻量级** - 总模型大小约 160MB，适合边缘设备

## 安装

```bash
# 克隆项目
git clone https://github.com/fangbb-coder/voice-bridge-light.git
cd voice-bridge-light

# 安装依赖
pip install -r requirements.txt

# 下载模型
python scripts/download_models.py
```

## 快速开始

```bash
# 启动服务
python main.py

# 测试 API
curl http://localhost:8000/health
```

## API 接口

### 处理语音
```bash
curl -X POST http://localhost:8000/voice/process \
  -H "Content-Type: application/json" \
  -d '{"audio_file": "test.wav", "language": "zh"}'
```

### 处理文本
```bash
curl -X POST http://localhost:8000/text/process \
  -H "Content-Type: application/json" \
  -d '{"text": "你好"}'
```

### 语音合成
```bash
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，我是语音助手", "voice": "zh_CN"}'
```

### 语音识别
```bash
curl -X POST http://localhost:8000/asr \
  -H "Content-Type: application/json" \
  -d '{"audio_file": "test.wav", "language": "zh"}'
```

## 配置

编辑 `config.yaml`：

```yaml
language: zh
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

## 平台支持

- ✅ Telegram
- ✅ 企业微信 (WeCom)
- ✅ 钉钉 (DingTalk)
- ✅ 飞书 (Feishu)
- ✅ WhatsApp
- ✅ QQ

## 项目结构

```
voice-bridge/
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

## 依赖

- openai-whisper
- piper-tts
- fastapi
- uvicorn
- pydantic
- pyyaml
- pydub
- numpy
- soundfile
- torch (可选，用于加速)

## 许可证

MIT
