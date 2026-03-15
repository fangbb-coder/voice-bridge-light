#!/usr/bin/env python3
"""
Voice Bridge Pro - 离线语音助手引擎
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
from voice.asr import VoiceASR
from voice.tts import VoiceTTS
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
        self.asr: Optional[VoiceASR] = None
        self.tts: Optional[VoiceTTS] = None
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
            logger.info("初始化 Voice Bridge Pro")
            logger.info("=" * 50)

            # 加载配置
            self.config = get_config()
            logger.info(f"语言: {self.config.language}")
            logger.info(f"唤醒词: {self.config.wake_word}")

            # 初始化 ASR
            try:
                logger.info(f"初始化 ASR 模型: {self.config.asr_model_dir}")
                self.asr = VoiceASR(self.config.asr_model_dir)
                logger.info("ASR 初始化成功")
            except Exception as e:
                logger.error(f"ASR 初始化失败: {e}")
                raise

            # 初始化 TTS
            try:
                logger.info(f"初始化 TTS 模型: {self.config.tts_model_dir}")
                voice = "af" if self.config.voice == "female" else "am"
                self.tts = VoiceTTS(self.config.tts_model_dir, voice=voice)
                logger.info("TTS 初始化成功")
            except Exception as e:
                logger.error(f"TTS 初始化失败: {e}")
                raise

            # 初始化助手
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
                    "app_id": adapter_config.app_id,
                    "app_secret": adapter_config.app_secret,
                    "extra": adapter_config.extra
                }

                adapter = get_adapter(name, config_dict)
                self.adapters[name] = adapter
                logger.info(f"适配器初始化成功: {name}")

            except Exception as e:
                logger.error(f"适配器初始化失败 {name}: {e}")

    def shutdown(self):
        """关闭应用"""
        with self.lock:
            logger.info("正在关闭应用...")
            self.initialized = False
            cleanup_temp_files(self.config.temp_dir if self.config else "temp", max_files=0)
            logger.info("应用已关闭")


# 全局状态实例
app_state = AppState()


# ========== 请求模型 ==========
class VoiceMessageRequest(BaseModel):
    """语音消息请求"""
    audio_file: str
    adapter: Optional[str] = None
    chat_id: Optional[str] = None


class TextMessageRequest(BaseModel):
    """文本消息请求"""
    text: str
    adapter: Optional[str] = None
    chat_id: Optional[str] = None


class WebhookRequest(BaseModel):
    """Webhook 请求"""
    adapter: str
    data: Dict[str, Any]


# ========== FastAPI 应用 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    app_state.init()
    yield
    app_state.shutdown()


app = FastAPI(
    title="Voice Bridge Pro",
    description="离线语音助手引擎 - 支持多平台",
    version="1.0.0",
    lifespan=lifespan
)


# ========== API 端点 ==========
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Voice Bridge Pro",
        "version": "1.0.0",
        "status": "running" if app_state.initialized else "initializing"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    if not app_state.initialized:
        raise HTTPException(status_code=503, detail="Service not ready")

    return {
        "status": "healthy",
        "asr_ready": app_state.asr.is_ready() if app_state.asr else False,
        "tts_ready": app_state.tts.is_ready() if app_state.tts else False,
        "adapters": list(app_state.adapters.keys())
    }


@app.post("/voice/process")
async def process_voice(request: VoiceMessageRequest):
    """
    处理语音消息

    - 转换音频格式
    - 语音识别
    - 生成回复
    - 语音合成
    """
    if not app_state.initialized:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # 检查文件
        audio_path = Path(request.audio_file)
        if not audio_path.exists():
            raise HTTPException(status_code=400, detail=f"音频文件不存在: {request.audio_file}")

        # 转换为 WAV
        from voice.audio_utils import generate_temp_path
        wav_path = generate_temp_path(app_state.config.temp_dir, suffix=".wav")
        convert_to_wav(str(audio_path), wav_path)

        # 语音识别
        text = app_state.asr.transcribe(wav_path)
        if not text:
            return JSONResponse({
                "success": False,
                "error": "语音识别失败",
                "text": None,
                "voice": None
            })

        # 处理消息
        result = app_state.assistant.process(text)

        # 如果指定了适配器和 chat_id，发送回复
        if request.adapter and request.chat_id and result:
            adapter = app_state.adapters.get(request.adapter)
            if adapter:
                if result.get("voice"):
                    adapter.send_voice(request.chat_id, result["voice"])
                else:
                    adapter.send_text(request.chat_id, result["text"])

        return JSONResponse({
            "success": True,
            "text": result.get("text") if result else None,
            "voice": result.get("voice") if result else None,
            "recognized_text": text
        })

    except Exception as e:
        logger.error(f"处理语音消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text/process")
async def process_text(request: TextMessageRequest):
    """处理文本消息"""
    if not app_state.initialized:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = app_state.assistant.process(request.text)

        # 如果指定了适配器和 chat_id，发送回复
        if request.adapter and request.chat_id and result:
            adapter = app_state.adapters.get(request.adapter)
            if adapter:
                if result.get("voice"):
                    adapter.send_voice(request.chat_id, result["voice"])
                else:
                    adapter.send_text(request.chat_id, result["text"])

        return JSONResponse({
            "success": True,
            "text": result.get("text") if result else None,
            "voice": result.get("voice") if result else None
        })

    except Exception as e:
        logger.error(f"处理文本消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/{adapter_name}")
async def webhook(adapter_name: str, request: Request):
    """
    接收 Webhook 消息

    各平台 Webhook 入口
    """
    if not app_state.initialized:
        raise HTTPException(status_code=503, detail="Service not ready")

    adapter = app_state.adapters.get(adapter_name)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"适配器未找到: {adapter_name}")

    try:
        # 解析请求体
        body = await request.body()
        data = json.loads(body)

        # 验证签名 (如果配置了)
        # 各平台签名验证逻辑不同，这里简化处理

        # 解析消息
        message = adapter.parse_webhook(data)
        if not message:
            return JSONResponse({"success": True, "message": "No message to process"})

        logger.info(f"收到 {adapter_name} 消息: {message.user.id}")

        # 处理消息
        if adapter.is_voice_message(message) and message.voice_file:
            # 下载语音
            voice_path = adapter.download_voice(message.voice_file)
            if voice_path:
                # 转换为 WAV
                from voice.audio_utils import generate_temp_path
                wav_path = generate_temp_path(app_state.config.temp_dir, suffix=".wav")
                convert_to_wav(voice_path, wav_path)

                # 语音识别
                text = app_state.asr.transcribe(wav_path)
                if text:
                    result = app_state.assistant.process(text)
                else:
                    result = {"text": "抱歉，我没能听清您说的话。", "voice": None}
            else:
                result = {"text": "抱歉，下载语音文件失败。", "voice": None}
        else:
            # 文本消息
            result = app_state.assistant.process(message.text)

        # 发送回复
        if result:
            if result.get("voice"):
                adapter.send_voice(message.chat_id, result["voice"])
            else:
                adapter.send_text(message.chat_id, result["text"])

        return JSONResponse({"success": True})

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook 处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/adapters")
async def list_available_adapters():
    """列出可用适配器"""
    return {
        "available": list_adapters(),
        "enabled": list(app_state.adapters.keys())
    }


@app.post("/reload")
async def reload():
    """重新加载配置"""
    try:
        reload_config()
        app_state.shutdown()
        app_state.init()
        return {"success": True, "message": "配置已重新加载"}
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 直接调用接口 (供 ClawHub 使用) ==========
def handle_voice_message(audio_file: str, adapter: str = None, chat_id: str = None) -> dict:
    """
    处理语音消息 (同步接口)

    Args:
        audio_file: 音频文件路径
        adapter: 适配器名称 (可选)
        chat_id: 聊天 ID (可选)

    Returns:
        处理结果
    """
    if not app_state.initialized:
        app_state.init()

    try:
        audio_path = Path(audio_file)
        if not audio_path.exists():
            return {"success": False, "error": f"音频文件不存在: {audio_file}"}

        # 转换为 WAV
        from voice.audio_utils import generate_temp_path
        wav_path = generate_temp_path(app_state.config.temp_dir, suffix=".wav")
        convert_to_wav(str(audio_path), wav_path)

        # 语音识别
        text = app_state.asr.transcribe(wav_path)
        if not text:
            return {"success": False, "error": "语音识别失败"}

        # 处理消息
        result = app_state.assistant.process(text)

        # 发送回复
        if adapter and chat_id and result:
            adapter_obj = app_state.adapters.get(adapter)
            if adapter_obj:
                if result.get("voice"):
                    adapter_obj.send_voice(chat_id, result["voice"])
                else:
                    adapter_obj.send_text(chat_id, result["text"])

        return {
            "success": True,
            "text": result.get("text") if result else None,
            "voice": result.get("voice") if result else None,
            "recognized_text": text
        }

    except Exception as e:
        logger.error(f"处理语音消息失败: {e}")
        return {"success": False, "error": str(e)}


def handle_text_message(text: str, adapter: str = None, chat_id: str = None) -> dict:
    """
    处理文本消息 (同步接口)

    Args:
        text: 文本内容
        adapter: 适配器名称 (可选)
        chat_id: 聊天 ID (可选)

    Returns:
        处理结果
    """
    if not app_state.initialized:
        app_state.init()

    try:
        result = app_state.assistant.process(text)

        # 发送回复
        if adapter and chat_id and result:
            adapter_obj = app_state.adapters.get(adapter)
            if adapter_obj:
                if result.get("voice"):
                    adapter_obj.send_voice(chat_id, result["voice"])
                else:
                    adapter_obj.send_text(chat_id, result["text"])

        return {
            "success": True,
            "text": result.get("text") if result else None,
            "voice": result.get("voice") if result else None
        }

    except Exception as e:
        logger.error(f"处理文本消息失败: {e}")
        return {"success": False, "error": str(e)}


# ========== 主入口 ==========
if __name__ == "__main__":
    import uvicorn

    # 获取端口
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"启动服务: {host}:{port}")
    uvicorn.run(app, host=host, port=port)
