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

## 使用方式

### 方式 1：纯函数调用（推荐，无 HTTP 服务）

```python
from core import stt, tts, process_voice, process_text

# 语音识别
result = stt("audio.wav", language="zh")
print(result)  # "你好"

# 语音合成
audio_file = tts("你好，我是语音助手", voice="zh_CN")
print(audio_file)  # "temp/xxx.wav"

# 处理语音消息
result = process_voice("audio.wav")
print(result["recognized_text"])  # 识别的文本
print(result["reply_text"])       # 回复文本
print(result["reply_voice"])      # 回复语音文件

# 处理文本消息
result = process_text("你好")
print(result["reply_text"])   # 回复文本
print(result["reply_voice"])  # 回复语音文件
```

### 方式 2：启动适配器管理器（自动处理多平台消息）

```bash
# 启动所有适配器（后台持续运行）
python start_adapters.py
```

适配器管理器功能：
- 自动轮询所有启用的平台（Telegram/QQ/企业微信/钉钉/飞书/WhatsApp）
- 收到语音消息：自动下载 → 语音识别 → 生成回复 → 语音合成 → 发送回复
- 收到文本消息：生成回复 → 语音合成（可选）→ 发送回复
- 后台持续运行，无需人工干预

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

- openai-whisper
- piper-tts
- fastapi（仅 HTTP 模式需要）
- uvicorn（仅 HTTP 模式需要）
- pydantic
- pyyaml
- pydub
- numpy
- soundfile
- torch（可选，用于加速）

## 项目结构

```
voice-bridge/
├── core.py                 # 核心功能（纯函数，无 HTTP）
├── start_adapters.py       # 启动适配器管理器
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
│   ├── manager.py          # 适配器管理器
│   ├── base.py             # 适配器基类
│   └── *.py                # 各平台适配器
└── scripts/
    └── download_models.py  # 模型下载
```

## 许可证

MIT
