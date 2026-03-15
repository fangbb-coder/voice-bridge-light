import os
from pathlib import Path
from typing import Optional

import sherpa_onnx

from utils.logger import setup_logger

logger = setup_logger(__name__)


class VoiceASR:
    """语音识别器 - 基于 sherpa-onnx"""

    def __init__(self, model_dir: str):
        """
        初始化语音识别器

        Args:
            model_dir: 模型目录路径
        """
        self.model_dir = Path(model_dir)
        self.recognizer: Optional[sherpa_onnx.OfflineRecognizer] = None

        self._init_recognizer()

    def _init_recognizer(self) -> None:
        """初始化识别器"""
        try:
            if not self.model_dir.exists():
                raise FileNotFoundError(f"ASR 模型目录不存在: {self.model_dir}")

            # 查找模型文件
            model_files = list(self.model_dir.rglob("*.onnx"))
            if not model_files:
                raise FileNotFoundError(f"在 {self.model_dir} 中未找到 .onnx 模型文件")

            # 使用第一个找到的模型
            model_path = model_files[0]
            logger.info(f"使用 ASR 模型: {model_path}")

            # 查找 tokens 文件
            tokens_file = self.model_dir / "tokens.txt"
            if not tokens_file.exists():
                tokens_file = self.model_dir / "chn_jpn_yue_eng_ko.txt"

            if not tokens_file.exists():
                raise FileNotFoundError(f"未找到 tokens 文件")

            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(model_path),
                tokens=str(tokens_file),
                use_itn=True,
                debug=False,
            )

            logger.info("ASR 识别器初始化成功")

        except Exception as e:
            logger.error(f"ASR 初始化失败: {e}")
            raise

    def transcribe(self, wav_file: str) -> Optional[str]:
        """
        识别语音文件

        Args:
            wav_file: WAV 文件路径

        Returns:
            识别文本，失败返回 None
        """
        try:
            if not self.recognizer:
                logger.error("ASR 识别器未初始化")
                return None

            wav_path = Path(wav_file)
            if not wav_path.exists():
                logger.error(f"音频文件不存在: {wav_file}")
                return None

            stream = self.recognizer.create_stream()
            stream.accept_waveform_file(str(wav_path))
            self.recognizer.decode_stream(stream)

            result = stream.result.text
            logger.debug(f"ASR 识别结果: {result}")

            return result if result else None

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return None

    def is_ready(self) -> bool:
        """检查识别器是否就绪"""
        return self.recognizer is not None
