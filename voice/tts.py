import os
from pathlib import Path
from typing import Optional

import sherpa_onnx
import soundfile as sf
import numpy as np

from utils.logger import setup_logger

logger = setup_logger(__name__)


class VoiceTTS:
    """语音合成器 - 基于 sherpa-onnx Kokoro"""

    # 支持的音色
    VOICES = {
        "af": "af",  # 美式英语女声 (默认)
        "am": "am",  # 美式英语男声
        "bf": "bf",  # 英式英语女声
        "bm": "bm",  # 英式英语男声
    }

    def __init__(self, model_dir: str, voice: str = "af"):
        """
        初始化语音合成器

        Args:
            model_dir: 模型目录路径
            voice: 音色选择 (af/am/bf/bm)
        """
        self.model_dir = Path(model_dir)
        self.voice = voice if voice in self.VOICES else "af"
        self.tts: Optional[sherpa_onnx.OfflineTts] = None

        self._init_tts()

    def _init_tts(self) -> None:
        """初始化 TTS"""
        try:
            if not self.model_dir.exists():
                raise FileNotFoundError(f"TTS 模型目录不存在: {self.model_dir}")

            # 查找模型文件
            model_files = list(self.model_dir.rglob("*.onnx"))
            if not model_files:
                raise FileNotFoundError(f"在 {self.model_dir} 中未找到 .onnx 模型文件")

            model_path = model_files[0]
            logger.info(f"使用 TTS 模型: {model_path}")

            # 查找 tokens 和 voices 文件
            tokens_file = self.model_dir / "tokens.txt"
            voices_file = self.model_dir / "voices.bin"

            if not tokens_file.exists():
                raise FileNotFoundError(f"未找到 tokens.txt")
            if not voices_file.exists():
                raise FileNotFoundError(f"未找到 voices.bin")

            self.tts = sherpa_onnx.OfflineTts(
                model=str(model_path),
                tokens=str(tokens_file),
                voices=str(voices_file),
                num_threads=2,
                debug=False,
            )

            logger.info(f"TTS 合成器初始化成功，当前音色: {self.voice}")

        except Exception as e:
            logger.error(f"TTS 初始化失败: {e}")
            raise

    def synthesize(
        self,
        text: str,
        output: str,
        speed: float = 1.0,
        sid: Optional[int] = None
    ) -> Optional[str]:
        """
        合成语音

        Args:
            text: 要合成的文本
            output: 输出文件路径
            speed: 语速 (0.5-2.0)
            sid: 音色 ID (可选)

        Returns:
            输出文件路径，失败返回 None
        """
        try:
            if not self.tts:
                logger.error("TTS 合成器未初始化")
                return None

            if not text or not text.strip():
                logger.warning("合成文本为空")
                return None

            # 限制语速范围
            speed = max(0.5, min(2.0, speed))

            # 生成语音
            audio = self.tts.generate(
                text=text,
                sid=sid if sid is not None else 0,
                speed=speed,
            )

            if audio is None or len(audio.samples) == 0:
                logger.error("语音合成失败: 无音频数据")
                return None

            # 确保输出目录存在
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            samples = np.array(audio.samples, dtype=np.float32)
            sf.write(str(output_path), samples, audio.sample_rate)

            logger.debug(f"语音合成完成: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return None

    def set_voice(self, voice: str) -> bool:
        """
        切换音色

        Args:
            voice: 音色代码

        Returns:
            是否切换成功
        """
        if voice in self.VOICES:
            self.voice = voice
            logger.info(f"切换音色为: {voice}")
            return True
        else:
            logger.warning(f"不支持的音色: {voice}")
            return False

    def is_ready(self) -> bool:
        """检查合成器是否就绪"""
        return self.tts is not None
