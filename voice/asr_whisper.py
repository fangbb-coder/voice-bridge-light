"""
Whisper STT 语音识别模块 - 轻量级离线语音识别
使用 openai-whisper 库
模型大小：tiny(39MB) / base(74MB) / small(244MB)
"""

import os
from pathlib import Path
from typing import Optional
import tempfile

from utils.logger import setup_logger

logger = setup_logger("voice.asr_whisper")


class WhisperASR:
    """Whisper 语音识别封装"""

    # 模型大小参考
    MODEL_SIZES = {
        "tiny": 39,      # 最快，准确率较低
        "base": 74,      # 平衡速度和准确率
        "small": 244,    # 较好准确率
        "medium": 769,   # 高准确率
        "large": 1550    # 最高准确率
    }

    def __init__(self, model_size: str = "base", model_dir: str = "models/whisper"):
        """
        初始化 Whisper ASR

        Args:
            model_size: 模型大小 (tiny/base/small/medium/large)
            model_dir: 模型缓存目录
        """
        self.model_size = model_size
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self._load_model()

    def _load_model(self) -> bool:
        """加载 Whisper 模型"""
        try:
            import whisper

            logger.info(f"正在加载 Whisper 模型: {self.model_size}")

            # 检查本地模型文件
            model_file = self.model_dir / f"{self.model_size}.pt"

            if model_file.exists():
                # 使用本地模型文件
                logger.info(f"使用本地模型: {model_file}")
                self.model = whisper.load_model(str(model_file))
            else:
                # 从网络下载
                logger.info(f"本地模型不存在，从网络下载: {self.model_size}")
                os.environ["WHISPER_CACHE_DIR"] = str(self.model_dir)
                self.model = whisper.load_model(self.model_size)

            logger.info(f"Whisper 模型加载完成: {self.model_size}")
            return True

        except ImportError:
            logger.error("openai-whisper 未安装，请运行: pip install openai-whisper")
            return False
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False

    def is_ready(self) -> bool:
        """检查是否可用"""
        return self.model is not None

    def transcribe(self, audio_file: str, language: Optional[str] = "zh") -> Optional[str]:
        """
        识别音频文件

        Args:
            audio_file: 音频文件路径
            language: 语言代码 (zh/en/ja/ko 等)

        Returns:
            识别文本，失败返回 None
        """
        if not self.is_ready():
            logger.error("模型未加载")
            return None

        try:
            audio_path = Path(audio_file)
            if not audio_path.exists():
                logger.error(f"音频文件不存在: {audio_file}")
                return None

            # 转录音频
            # 使用 initial_prompt 提示模型输出简体中文
            initial_prompt = "以下是普通话的句子。" if language == "zh" else None

            result = self.model.transcribe(
                str(audio_file),
                language=language,
                fp16=False,  # CPU 运行禁用 fp16
                initial_prompt=initial_prompt
            )

            text = result.get("text", "").strip()

            # 繁体转简体（如果安装了 opencc）
            if language == "zh":
                try:
                    import opencc
                    converter = opencc.OpenCC('t2s')
                    text = converter.convert(text)
                except ImportError:
                    pass  # 未安装 opencc，保持原样

            logger.info(f"识别结果: {text}")

            return text

        except Exception as e:
            logger.error(f"识别失败: {e}")
            return None

    def transcribe_with_timestamps(self, audio_file: str, language: Optional[str] = "zh") -> list:
        """
        识别音频并返回带时间戳的结果

        Args:
            audio_file: 音频文件路径
            language: 语言代码

        Returns:
            带时间戳的片段列表
        """
        if not self.is_ready():
            return []

        try:
            # 使用 initial_prompt 提示模型输出简体中文
            initial_prompt = "以下是普通话的句子。" if language == "zh" else None

            result = self.model.transcribe(
                str(audio_file),
                language=language,
                fp16=False,
                verbose=False,
                initial_prompt=initial_prompt
            )

            segments = result.get("segments", [])

            # 繁体转简体（如果安装了 opencc）
            if language == "zh":
                try:
                    import opencc
                    converter = opencc.OpenCC('t2s')
                    for seg in segments:
                        seg["text"] = converter.convert(seg["text"])
                except ImportError:
                    pass  # 未安装 opencc，保持原样

            return [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                }
                for seg in segments
            ]

        except Exception as e:
            logger.error(f"识别失败: {e}")
            return []

    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            "size": self.model_size,
            "size_mb": self.MODEL_SIZES.get(self.model_size, 0),
            "ready": self.is_ready(),
            "model_dir": str(self.model_dir)
        }

    @classmethod
    def get_available_models(cls) -> list:
        """获取可用模型列表"""
        return list(cls.MODEL_SIZES.keys())


def quick_transcribe(audio_file: str, model_size: str = "base", language: str = "zh") -> Optional[str]:
    """
    快速识别函数（无需实例化）

    Args:
        audio_file: 音频文件路径
        model_size: 模型大小
        language: 语言代码

    Returns:
        识别文本
    """
    asr = WhisperASR(model_size=model_size)
    return asr.transcribe(audio_file, language)
