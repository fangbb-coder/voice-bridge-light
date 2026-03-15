"""
Piper TTS 语音合成模块 - 轻量级离线 Neural TTS
模型大小：约 50-100MB（取决于语音质量）
"""

import os
import subprocess
import tempfile
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

    def _check_piper_install(self) -> bool:
        """检查 piper-tts 是否已安装"""
        try:
            import piper
            return True
        except ImportError:
            logger.warning("Piper TTS 未安装，请运行: pip install piper-tts")
            return False

    def is_ready(self) -> bool:
        """检查是否可用"""
        return self.model_path.exists() and self.json_path.exists()

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

            # 构建 piper 命令
            cmd = [
                "piper",
                "--model", str(self.model_path),
                "--config", str(self.json_path),
                "--output_file", str(output_file)
            ]

            # 运行 piper
            process = subprocess.run(
                cmd,
                input=text.encode('utf-8'),
                capture_output=True
            )

            if process.returncode != 0:
                logger.error(f"Piper 合成失败: {process.stderr.decode()}")
                return None

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
            cmd = [
                "piper",
                "--model", str(self.model_path),
                "--config", str(self.json_path),
                "--output_file", "-"  # 输出到 stdout
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 发送文本
            process.stdin.write(text.encode('utf-8'))
            process.stdin.close()

            # 读取音频数据
            chunk_size = 4096
            while True:
                chunk = process.stdout.read(chunk_size)
                if not chunk:
                    break
                yield chunk

            process.wait()

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
