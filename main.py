#!/usr/bin/env python3
"""
Voice Bridge - 离线语音助手引擎
使用 Whisper + Piper，模型总大小约 160MB
支持多平台适配器：Telegram、企业微信、钉钉、飞书、WhatsApp、QQ
"""

import os
import sys
import json
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import get_config, reload_config
from voice.asr_whisper import WhisperASR
from voice.tts_piper import PiperTTS
from voice.audio_utils import convert_to_wav, cleanup_temp_files
from assistant.voice_assistant import VoiceAssistant
from adapters import get_adapter, list_adapters, BaseAdapter
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ========== 全局状态 ==========
class AppState:
    """应用状态管理"""
    def __init__(self):
        self.config = None
        self.asr: Optional[WhisperASR] = None
        self.tts: Optional[PiperTTS] = None
        self.assistant: Optional[VoiceAssistant] = None
        self.adapters: Dict[str, BaseAdapter] = {}
        self.initialized = False
        self.lock = threading.Lock()

    def init(self):
        """初始化所有组件"""
        with self.lock:
            if self.initialized:
                return

            logger.info("=" * 50)
            logger.info("初始化 Voice Bridge")
            logger.info("=" * 50)

            # 加载配置
            self.config = get_config()
            logger.info(f"语言: {self.config.language}")
            logger.info(f"唤醒词: {self.config.wake_word}")

            # 设置 Whisper 缓存目录
            whisper_cache = Path("models/whisper")
            whisper_cache.mkdir(parents=True, exist_ok=True)
            os.environ["WHISPER_CACHE_DIR"] = str(whisper_cache)

            # 初始化 ASR (Whisper)
            try:
                logger.info("初始化 Whisper ASR (base, 74MB)")
                self.asr = WhisperASR(model_size="base")
                if self.asr.is_ready():
                    logger.info("ASR 初始化成功")
                else:
                    logger.warning("ASR 将在首次使用时加载模型")
            except Exception as e:
                logger.error(f"ASR 初始化失败: {e}")
                logger.info("请确保已安装: pip install openai-whisper")

            # 初始化 TTS (Piper)
            try:
                language = "zh_CN" if self.config.language == "zh" else "en_US"
                logger.info(f"初始化 Piper TTS ({language})")
                self.tts = PiperTTS(language=language)
                if self.tts.is_ready():
                    logger.info("TTS 初始化成功")
                else:
                    logger.warning(f"TTS 模型未找到，请运行: python scripts/download_models.py")
            except Exception as e:
                logger.error(f"TTS 初始化失败: {e}")
                logger.info("请确保已安装: pip install piper-tts")

            # 初始化助手
            if self.asr and self.tts:
                self.assistant = VoiceAssistant(self.asr, self.tts)
                logger.info("语音助手初始化成功")

            # 初始化适配器
            self._init_adapters()

            self.initialized = True
            logger.info("=" * 50)
            logger.info("初始化完成")
            logger.info("=" * 50)

    def _init_adapters(self):
        """初始化启用的适配器"""
        for name, adapter_config in self.config.adapters.items():
            if not adapter_config.enabled:
                continue

            try:
                config_dict = {
                    "token": adapter_config.token,
                    "webhook_secret": adapter_config.webhook_secret,
                    "api_key": adapter_config.api_key,
                    "api_secret": adapter_config.api_secret,
                    "base_url": adapter_config.base_url
                }

                adapter = get_adapter(name, config_dict)
                if adapter:
                    self.adapters[name] = adapter
                    logger.info(f"适配器 {name} 初始化成功")

            except Exception as e:
                logger.error(f"适配器 {name} 初始化失败: {e}")

    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            "initialized": self.initialized,
            "asr_ready": self.asr.is_ready() if self.asr else False,
            "tts_ready": self.tts.is_ready() if self.tts else False,
            "adapters": list(self.adapters.keys()),
            "language": self.config.language if self.config else None
        }

# 全局状态实例
app_state = AppState()

# ========== 数据模型 ==========
class VoiceProcessRequest(BaseModel):
    audio_file: str
    language: Optional[str] = None

class TextProcessRequest(BaseModel):
    text: str
    reply_with_voice: bool = True

class TextToSpeechRequest(BaseModel):
    text: str
    voice: Optional[str] = None

class WebhookRequest(BaseModel):
    adapter: str
    payload: Dict[str, Any]

# ========== 业务逻辑 ==========
def handle_voice_message(audio_file: str, language: Optional[str] = None) -> dict:
    """
    处理语音消息

    Args:
        audio_file: 音频文件路径
        language: 语言代码

    Returns:
        处理结果
    """
    if not app_state.initialized:
        app_state.init()

    try:
        # 验证文件
        from voice.audio_utils import validate_audio_file
        is_valid, error = validate_audio_file(audio_file)
        if not is_valid:
            return {"success": False, "error": error}

        # 转换为 wav
        wav_file = convert_to_wav(audio_file)
        if not wav_file:
            return {"success": False, "error": "音频转换失败"}

        # 识别语音
        lang = language or app_state.config.language
        text = app_state.asr.transcribe(wav_file, language=lang)

        if not text:
            return {"success": False, "error": "语音识别失败"}

        # 生成回复
        reply_text = app_state.assistant.generate_reply(text)

        # 合成语音回复
        reply_voice = None
        if app_state.config.auto_voice_reply:
            reply_voice = app_state.tts.synthesize(reply_text)

        # 清理临时文件
        cleanup_temp_files(app_state.config.max_temp_files)

        return {
            "success": True,
            "recognized_text": text,
            "reply_text": reply_text,
            "reply_voice": reply_voice
        }

    except Exception as e:
        logger.error(f"处理语音消息失败: {e}")
        return {"success": False, "error": str(e)}

def handle_text_message(text: str, reply_with_voice: bool = True) -> dict:
    """
    处理文本消息

    Args:
        text: 文本消息
        reply_with_voice: 是否用语音回复

    Returns:
        处理结果
    """
    if not app_state.initialized:
        app_state.init()

    try:
        # 生成回复
        reply_text = app_state.assistant.generate_reply(text)

        # 合成语音
        reply_voice = None
        if reply_with_voice and app_state.config.auto_voice_reply:
            reply_voice = app_state.tts.synthesize(reply_text)

        return {
            "success": True,
            "reply_text": reply_text,
            "reply_voice": reply_voice
        }

    except Exception as e:
        logger.error(f"处理文本消息失败: {e}")
        return {"success": False, "error": str(e)}

# ========== FastAPI 应用 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    app_state.init()
    yield
    # 关闭时清理
    logger.info("应用关闭")

app = FastAPI(
    title="Voice Bridge",
    description="离线语音助手引擎（Whisper + Piper）",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """健康检查"""
    status = app_state.get_status()
    return {
        "status": "healthy" if status["initialized"] else "initializing",
        **status
    }

@app.get("/models")
async def get_models_info():
    """获取模型信息"""
    info = {
        "asr": app_state.asr.get_model_info() if app_state.asr else None,
        "tts": app_state.tts.get_model_info() if app_state.tts else None
    }
    return info

@app.post("/voice/process")
async def process_voice(request: VoiceProcessRequest):
    """处理语音"""
    result = handle_voice_message(request.audio_file, request.language)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/text/process")
async def process_text(request: TextProcessRequest):
    """处理文本"""
    result = handle_text_message(request.text, request.reply_with_voice)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/tts")
async def text_to_speech(request: TextToSpeechRequest):
    """文本转语音"""
    if not app_state.tts:
        raise HTTPException(status_code=503, detail="TTS 未初始化")

    voice_file = app_state.tts.synthesize(request.text)
    if not voice_file:
        raise HTTPException(status_code=500, detail="语音合成失败")

    return {"success": True, "voice_file": voice_file}

@app.post("/asr")
async def speech_to_text(request: VoiceProcessRequest):
    """语音转文本"""
    if not app_state.asr:
        raise HTTPException(status_code=503, detail="ASR 未初始化")

    # 转换为 wav
    wav_file = convert_to_wav(request.audio_file)
    if not wav_file:
        raise HTTPException(status_code=400, detail="音频转换失败")

    # 识别
    text = app_state.asr.transcribe(wav_file, request.language)
    if not text:
        raise HTTPException(status_code=500, detail="语音识别失败")

    return {"success": True, "text": text}

@app.get("/adapters")
async def get_adapters():
    """获取适配器列表"""
    return {
        "available": list_adapters(),
        "enabled": list(app_state.adapters.keys())
    }

@app.post("/webhook/{adapter_name}")
async def webhook(adapter_name: str, request: Request):
    """接收适配器 Webhook"""
    if adapter_name not in app_state.adapters:
        raise HTTPException(status_code=404, detail=f"适配器 {adapter_name} 未启用")

    try:
        payload = await request.json()
    except:
        payload = {}

    adapter = app_state.adapters[adapter_name]

    try:
        # 解析消息
        message = adapter.parse_webhook(payload)
        if not message:
            return {"success": False, "error": "无法解析消息"}

        # 处理消息
        if message.voice_url:
            # 下载语音文件
            voice_file = adapter.download_voice(message.voice_url)
            result = handle_voice_message(voice_file)
        else:
            result = handle_text_message(message.text)

        # 发送回复
        if result["success"]:
            adapter.send_message(
                chat_id=message.chat_id,
                text=result["reply_text"],
                voice_file=result.get("reply_voice")
            )

        return {"success": True}

    except Exception as e:
        logger.error(f"Webhook 处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 主入口 ==========
if __name__ == "__main__":
    import uvicorn

    # 获取配置
    config = get_config()

    # 启动服务
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=False,
        log_level="info"
    )
