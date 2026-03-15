#!/usr/bin/env python3
"""
Voice Bridge - 核心功能模块（无 HTTP 服务）
纯函数调用方式使用 TTS/STT 功能
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from voice.asr_whisper import WhisperASR
from voice.tts_piper import PiperTTS
from voice.audio_utils import convert_to_wav, cleanup_temp_files
from assistant.voice_assistant import VoiceAssistant
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ========== 全局状态 ==========
class CoreState:
    """核心状态管理（无服务）"""
    def __init__(self):
        self.config = None
        self.asr: Optional[WhisperASR] = None
        self.tts: Optional[PiperTTS] = None
        self.assistant: Optional[VoiceAssistant] = None
        self.initialized = False

    def init(self):
        """初始化所有组件"""
        if self.initialized:
            return

        logger.info("=" * 50)
        logger.info("初始化 Voice Bridge (Core Mode)")
        logger.info("=" * 50)

        # 加载配置
        self.config = get_config()
        logger.info(f"语言: {self.config.language}")

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

        # 初始化助手
        if self.asr and self.tts:
            self.assistant = VoiceAssistant(self.asr, self.tts)
            logger.info("语音助手初始化成功")

        self.initialized = True
        logger.info("=" * 50)
        logger.info("初始化完成")
        logger.info("=" * 50)

# 全局状态实例
core_state = CoreState()

# ========== 纯函数 API ==========
def speech_to_text(audio_file: str, language: Optional[str] = None) -> Dict[str, Any]:
    """
    语音识别 - 将音频转换为文本

    Args:
        audio_file: 音频文件路径
        language: 语言代码 (zh/en/ja/ko)

    Returns:
        {"success": True, "text": "识别文本"} 或 {"success": False, "error": "错误信息"}
    """
    if not core_state.initialized:
        core_state.init()

    if not core_state.asr:
        return {"success": False, "error": "ASR 未初始化"}

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
        lang = language or core_state.config.language
        text = core_state.asr.transcribe(wav_file, language=lang)

        if not text:
            return {"success": False, "error": "语音识别失败"}

        return {"success": True, "text": text}

    except Exception as e:
        logger.error(f"语音识别失败: {e}")
        return {"success": False, "error": str(e)}


def text_to_speech(text: str, voice: Optional[str] = None) -> Dict[str, Any]:
    """
    语音合成 - 将文本转换为音频

    Args:
        text: 要合成的文本
        voice: 音色 (zh_CN/en_US/en_US_low)，默认使用配置中的中文女声

    Returns:
        {"success": True, "audio_file": "音频文件路径"} 或 {"success": False, "error": "错误信息"}
    """
    if not core_state.initialized:
        core_state.init()

    if not core_state.tts:
        return {"success": False, "error": "TTS 未初始化"}

    try:
        # 如果没有指定音色，使用配置中的默认音色（中文女声）
        if voice is None:
            # 从配置中获取默认语言，如果配置中没有则使用 zh_CN
            voice = 'zh_CN'
            if hasattr(core_state.config, 'tts') and hasattr(core_state.config.tts, 'language'):
                voice = core_state.config.tts.language
            logger.debug(f"使用默认 TTS 音色: {voice}")

        # 如果需要切换音色
        if voice != core_state.tts.language:
            logger.info(f"切换 TTS 音色: {voice}")
            core_state.tts = PiperTTS(language=voice)

        # 合成语音
        audio_file = core_state.tts.synthesize(text)

        if not audio_file:
            return {"success": False, "error": "语音合成失败"}

        return {"success": True, "audio_file": audio_file}

    except Exception as e:
        logger.error(f"语音合成失败: {e}")
        return {"success": False, "error": str(e)}


def process_voice(audio_file: str, language: Optional[str] = None) -> Dict[str, Any]:
    """
    处理语音消息 - 识别并生成回复

    Args:
        audio_file: 音频文件路径
        language: 语言代码

    Returns:
        {
            "success": True,
            "recognized_text": "识别的文本",
            "reply_text": "回复文本",
            "reply_voice": "回复语音文件路径"
        }
    """
    if not core_state.initialized:
        core_state.init()

    try:
        # 语音识别
        stt_result = speech_to_text(audio_file, language)
        if not stt_result["success"]:
            return stt_result

        recognized_text = stt_result["text"]

        # 生成回复
        if core_state.assistant:
            reply_text = core_state.assistant.generate_reply(recognized_text)
        else:
            reply_text = f"你说的是: {recognized_text}"

        # 合成回复语音
        reply_voice = None
        if core_state.config.auto_voice_reply:
            tts_result = text_to_speech(reply_text)
            if tts_result["success"]:
                reply_voice = tts_result["audio_file"]

        # 清理临时文件
        cleanup_temp_files(core_state.config.max_temp_files)

        return {
            "success": True,
            "recognized_text": recognized_text,
            "reply_text": reply_text,
            "reply_voice": reply_voice
        }

    except Exception as e:
        logger.error(f"处理语音失败: {e}")
        return {"success": False, "error": str(e)}


def process_text(text: str, reply_with_voice: bool = True) -> Dict[str, Any]:
    """
    处理文本消息 - 生成回复

    Args:
        text: 输入文本
        reply_with_voice: 是否用语音回复

    Returns:
        {
            "success": True,
            "reply_text": "回复文本",
            "reply_voice": "回复语音文件路径" (如果 reply_with_voice=True)
        }
    """
    if not core_state.initialized:
        core_state.init()

    try:
        # 生成回复
        if core_state.assistant:
            reply_text = core_state.assistant.generate_reply(text)
        else:
            reply_text = f"收到: {text}"

        # 合成语音
        reply_voice = None
        if reply_with_voice and core_state.config.auto_voice_reply:
            tts_result = text_to_speech(reply_text)
            if tts_result["success"]:
                reply_voice = tts_result["audio_file"]

        return {
            "success": True,
            "reply_text": reply_text,
            "reply_voice": reply_voice
        }

    except Exception as e:
        logger.error(f"处理文本失败: {e}")
        return {"success": False, "error": str(e)}


# ========== 便捷函数 ==========
def stt(audio_file: str, language: Optional[str] = None) -> str:
    """
    语音识别简写函数

    Returns:
        识别文本，失败返回空字符串
    """
    result = speech_to_text(audio_file, language)
    return result.get("text", "") if result["success"] else ""


def tts(text: str, voice: Optional[str] = None) -> str:
    """
    语音合成简写函数

    Returns:
        音频文件路径，失败返回空字符串
    """
    result = text_to_speech(text, voice)
    return result.get("audio_file", "") if result["success"] else ""


# ========== 主入口 ==========
if __name__ == "__main__":
    # 测试
    core_state.init()
    print("Voice Bridge Core 已初始化")
    print("可用函数: stt(), tts(), process_voice(), process_text()")
