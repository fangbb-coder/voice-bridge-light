"""
Piper TTS 语音合成模块 - 轻量级离线 Neural TTS
模型大小：约 50-100MB（取决于语音质量）
"""

import os
import tempfile
import wave
import io
from pathlib import Path
from typing import Optional, Tuple

from utils.logger import setup_logger

logger = setup_logger("voice.tts_piper")


class PiperTTS:
    """Piper TTS 封装"""

    # 推荐的轻量级模型
    MODELS = {
        "zh_CN": {
            "name": "zh_CN-huayan-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
            "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json",
            "size_mb": 60,
            "language": "zh_CN",
            "speaker": "huayan"
        },
        "en_US": {
            "name": "en_US-lessac-medium",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
            "size_mb": 60,
            "language": "en_US",
            "speaker": "lessac"
        },
        "en_US_low": {
            "name": "en_US-lessac-low",
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx",
            "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx.json",
            "size_mb": 25,
            "language": "en_US",
            "speaker": "lessac"
        }
    }

    def __init__(self, model_dir: str = "models/piper", language: str = "zh_CN"):
        """
        初始化 Piper TTS

        Args:
            model_dir: 模型目录
            language: 语言代码 (zh_CN/en_US/en_US_low)
        """
        self.model_dir = Path(model_dir)
        self.language = language
        self.model_config = self.MODELS.get(language, self.MODELS["zh_CN"])

        self.model_path = self.model_dir / f"{self.model_config['name']}.onnx"
        self.json_path = self.model_dir / f"{self.model_config['name']}.onnx.json"

        self._check_piper_install()
        self._load_voice()

    def _check_piper_install(self) -> bool:
        """检查 piper-tts 是否已安装"""
        try:
            import piper
            return True
        except ImportError:
            logger.warning("Piper TTS 未安装，请运行: pip install piper-tts")
            return False

    def _load_voice(self):
        """加载 Piper 语音模型"""
        try:
            from piper import PiperVoice

            if not self.is_ready():
                logger.warning(f"模型文件不存在: {self.model_path}")
                self.voice = None
                return

            # 加载模型
            self.voice = PiperVoice.load(str(self.model_path), str(self.json_path))
            logger.info(f"Piper 语音模型加载成功: {self.model_config['name']}")

        except Exception as e:
            logger.error(f"加载 Piper 语音模型失败: {e}")
            self.voice = None

    def is_ready(self) -> bool:
        """检查是否可用"""
        return self.model_path.exists() and self.json_path.exists() and self.voice is not None

    def synthesize(self, text: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        合成语音

        Args:
            text: 要合成的文本
            output_file: 输出文件路径（可选）

        Returns:
            输出文件路径，失败返回 None
        """
        if not self.is_ready():
            logger.error(f"模型未准备好: {self.model_path}")
            return None

        try:
            # 创建临时输出文件
            if output_file is None:
                fd, output_file = tempfile.mkstemp(suffix=".wav")
                os.close(fd)

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 使用 Piper Python API 合成
            with wave.open(output_file, "wb") as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(22050)  # 采样率

                # 合成音频
                for audio_bytes in self.voice.synthesize_stream_raw(text):
                    wav_file.writeframes(audio_bytes)

            logger.info(f"语音合成完成: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return None

    def synthesize_stream(self, text: str):
        """
        流式合成（生成器，用于实时播放）

        Args:
            text: 要合成的文本

        Yields:
            音频数据块
        """
        if not self.is_ready():
            logger.error("模型未准备好")
            return

        try:
            # 使用 Piper Python API 流式合成
            for audio_bytes in self.voice.synthesize_stream_raw(text):
                yield audio_bytes

        except Exception as e:
            logger.error(f"流式合成失败: {e}")

    @classmethod
    def get_available_voices(cls) -> list:
        """获取可用的语音列表"""
        return list(cls.MODELS.keys())

    def get_model_info(self) -> dict:
        """获取当前模型信息"""
        return {
            "name": self.model_config["name"],
            "language": self.model_config["language"],
            "size_mb": self.model_config["size_mb"],
            "model_path": str(self.model_path),
            "ready": self.is_ready()
        }
