# Voice Bridge

离线语音助手引擎，使用 Whisper + Piper，模型总大小约 160MB。

## 特性

- 🎤 **语音识别 (ASR)** - Whisper base (74MB)，支持多语言，自动繁体转简体
- 🔊 **语音合成 (TTS)** - Piper Neural TTS (25-60MB)，自然流畅
- 🤖 **语音助手** - 支持唤醒词、命令处理
- 💬 **多平台支持** - Telegram、企业微信、钉钉、飞书、WhatsApp、QQ
- 🚀 **轻量级** - 总模型大小约 160MB，适合边缘设备
- ⚡ **自动处理** - 后台持续运行，自动接收和回复消息
- 🔧 **systemd 服务** - 支持开机自启和自动重启
- 🔄 **兼容接口** - 提供 Edge TTS 兼容脚本，便于迁移

## 使用方法

### 方式 1：纯函数调用（推荐，无 HTTP 服务）

```python
from core import stt, tts, process_voice, process_text

# 语音识别
text = stt("audio.wav", language="zh")
print(text)  # "你好"

# 语音合成
audio_file = tts("你好，我是语音助手", voice="zh_CN")
print(audio_file)  # "temp/xxx.wav"

# 处理语音消息（识别 + 回复）
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

# 或使用适配器管理器 API
python -c "from adapters.manager import start_adapters; start_adapters()"
```

适配器管理器功能：
- 自动轮询所有启用的平台（Telegram/QQ/企业微信/钉钉/飞书/WhatsApp）
- 收到语音消息：自动下载 → 语音识别 → 生成回复 → 语音合成 → 发送回复
- 收到文本消息：生成回复 → 语音合成（可选）→ 发送回复
- 后台持续运行，无需人工干预

## 配置

编辑 `config.yaml`：

```yaml
# 基础配置
language: zh
voice: female
wake_word: "hey claw"
auto_voice_reply: true

# 模型配置
whisper_model_size: base  # tiny/base/small
piper_language: zh_CN     # zh_CN/en_US/en_US_low

# 回复配置
reply:
  # 语音消息的回复模式
  # - auto: 自动（语音消息用语音回复，文本消息用文本回复）- 默认
  # - text_only: 仅文本回复
  # - voice_only: 仅语音回复
  # - text_and_voice: 文本+语音回复
  voice_reply_mode: "auto"

  # 文本消息的回复模式
  # - text_only: 仅文本回复 - 默认
  # - voice_only: 仅语音回复
  # - text_and_voice: 文本+语音回复
  text_reply_mode: "text_only"

  # 语音消息回复时是否包含识别文本
  include_recognized_text: true

# 适配器配置（启用需要的平台）
adapters:
  telegram:
    enabled: true
    token: "YOUR_BOT_TOKEN"
    poll_interval: 5  # 轮询间隔（秒）

  qq:
    enabled: true
    token: "YOUR_BOT_TOKEN"
    app_id: "YOUR_APP_ID"

  wecom:
    enabled: false
    corp_id: "YOUR_CORP_ID"
    corp_secret: "YOUR_CORP_SECRET"
    agent_id: "YOUR_AGENT_ID"

  dingtalk:
    enabled: false
    app_key: "YOUR_APP_KEY"
    app_secret: "YOUR_APP_SECRET"

  feishu:
    enabled: false
    app_id: "YOUR_APP_ID"
    app_secret: "YOUR_APP_SECRET"

  whatsapp:
    enabled: false
    phone_number_id: "YOUR_PHONE_NUMBER_ID"
    access_token: "YOUR_ACCESS_TOKEN"
```

## 模型下载

```bash
# 下载全部模型（约 160MB）
python scripts/download_models.py all

# 仅下载 Whisper ASR（74MB）
python scripts/download_models.py whisper

# 仅下载中文 TTS（60MB）
python scripts/download_models.py piper_zh

# 仅下载英文 TTS（25MB）
python scripts/download_models.py piper_en
```

## 支持的语言

### Whisper ASR
- 中文 (zh) - 支持自动繁体转简体
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
- piper-tts
- fastapi（仅 HTTP 模式需要）
- uvicorn（仅 HTTP 模式需要）
- pydantic
- pyyaml
- pydub
- numpy
- soundfile
- requests

可选：
- opencc-python-reimplemented - 繁体转简体（中文识别更准确）
- torch - 加速 Whisper 推理

## systemd 服务部署

Linux 系统可配置为 systemd 服务，实现开机自启：

```bash
# 复制服务文件
sudo cp scripts/voice-bridge.service /etc/systemd/system/

# 编辑工作目录和用户名
sudo systemctl edit voice-bridge.service
# 修改 WorkingDirectory 和 User

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable voice-bridge
sudo systemctl start voice-bridge

# 查看状态
sudo systemctl status voice-bridge
```

## Edge TTS 兼容

如需兼容原有 Edge TTS 调用，使用提供的适配脚本：

```bash
# 原 edge-tts 调用方式
python scripts/edge_tts_speak.py "你好" -o output.wav -v xiaoxiao

# 实际调用 Voice Bridge Piper
# 支持语音映射：xiaoxiao → zh_CN, en → en_US
```

## 部署测试

运行测试脚本验证安装：

```bash
python test_skill.py
```

预期输出：8/8 测试通过

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
│   ├── asr_whisper.py      # Whisper 语音识别（支持繁体转简体）
│   ├── tts_piper.py        # Piper 语音合成
│   └── audio_utils.py      # 音频处理
├── assistant/
│   └── voice_assistant.py  # 语音助手逻辑
├── adapters/               # 多平台适配器
│   ├── manager.py          # 适配器管理器
│   ├── base.py             # 适配器基类
│   ├── telegram.py
│   ├── qq.py
│   ├── wecom.py
│   ├── dingtalk.py
│   ├── feishu.py
│   └── whatsapp.py
└── scripts/
    ├── download_models.py  # 模型下载
    ├── voice-bridge.service # systemd 服务配置
    └── edge_tts_speak.py   # Edge TTS 兼容脚本
```

## 适配器管理器架构

```
┌─────────────────────────────────────────────────────────┐
│                    AdapterManager                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Telegram   │  │     QQ      │  │   WeCom     │     │
│  │  Adapter    │  │  Adapter    │  │  Adapter    │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  DingTalk   │  │   Feishu    │  │  WhatsApp   │     │
│  │  Adapter    │  │  Adapter    │  │  Adapter    │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         └────────────────┴────────────────┘             │
│                         │                               │
│                         ▼                               │
│              ┌─────────────────────┐                    │
│              │   process_message   │                    │
│              │   (语音/文本处理)    │                    │
│              └─────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## 许可证

MIT
