import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from contextlib import contextmanager

from pydub import AudioSegment

from utils.logger import setup_logger

logger = setup_logger(__name__)


class AudioConversionError(Exception):
    """音频转换异常"""
    pass


def convert_to_wav(
    input_file: str,
    output_file: Optional[str] = None,
    sample_rate: int = 16000,
    channels: int = 1
) -> str:
    """
    将音频文件转换为 WAV 格式

    Args:
        input_file: 输入音频文件路径
        output_file: 输出 WAV 文件路径 (为 None 则自动生成)
        sample_rate: 目标采样率
        channels: 目标声道数

    Returns:
        输出文件路径

    Raises:
        AudioConversionError: 转换失败
    """
    try:
        input_path = Path(input_file)
        if not input_path.exists():
            raise AudioConversionError(f"输入文件不存在: {input_file}")

        # 自动生成输出路径
        if output_file is None:
            output_file = str(input_path.with_suffix('.wav'))

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载音频
        audio = AudioSegment.from_file(str(input_path))

        # 转换为单声道
        if channels == 1 and audio.channels > 1:
            audio = audio.set_channels(1)

        # 转换采样率
        if audio.frame_rate != sample_rate:
            audio = audio.set_frame_rate(sample_rate)

        # 导出为 WAV
        audio.export(str(output_path), format="wav")

        logger.debug(f"音频转换完成: {input_file} -> {output_file}")
        return str(output_path)

    except Exception as e:
        logger.error(f"音频转换失败: {e}")
        raise AudioConversionError(f"转换失败: {e}")


def get_audio_info(file_path: str) -> dict:
    """
    获取音频文件信息

    Args:
        file_path: 音频文件路径

    Returns:
        包含时长、采样率、声道数等信息的字典
    """
    try:
        audio = AudioSegment.from_file(file_path)
        return {
            "duration_ms": len(audio),
            "duration_sec": len(audio) / 1000,
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "bitrate": audio.frame_width * 8 if hasattr(audio, 'frame_width') else None,
            "format": Path(file_path).suffix.lower()
        }
    except Exception as e:
        logger.error(f"获取音频信息失败: {e}")
        return {}


def generate_temp_path(temp_dir: str = "temp", suffix: str = ".wav") -> str:
    """
    生成临时文件路径

    Args:
        temp_dir: 临时目录
        suffix: 文件后缀

    Returns:
        临时文件路径
    """
    temp_path = Path(temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{suffix}"
    return str(temp_path / filename)


@contextmanager
def temp_audio_file(temp_dir: str = "temp", suffix: str = ".wav"):
    """
    临时音频文件上下文管理器

    使用示例:
        with temp_audio_file() as tmp_path:
            # 使用 tmp_path
            pass
        # 文件自动删除
    """
    temp_path = generate_temp_path(temp_dir, suffix)
    try:
        yield temp_path
    finally:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")


def cleanup_temp_files(temp_dir: str = "temp", max_files: int = 100) -> int:
    """
    清理临时文件，只保留最新的 N 个

    Args:
        temp_dir: 临时目录
        max_files: 最大保留文件数

    Returns:
        删除的文件数
    """
    try:
        temp_path = Path(temp_dir)
        if not temp_path.exists():
            return 0

        files = sorted(
            temp_path.iterdir(),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        deleted = 0
        for f in files[max_files:]:
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass

        if deleted > 0:
            logger.info(f"清理了 {deleted} 个临时文件")

        return deleted

    except Exception as e:
        logger.error(f"清理临时文件失败: {e}")
        return 0


def validate_audio_file(file_path: str, max_duration_sec: float = 300) -> Tuple[bool, str]:
    """
    验证音频文件

    Args:
        file_path: 音频文件路径
        max_duration_sec: 最大允许时长（秒）

    Returns:
        (是否有效, 错误信息)
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return False, "文件不存在"

        if path.stat().st_size == 0:
            return False, "文件为空"

        info = get_audio_info(file_path)

        if not info:
            return False, "无法读取音频信息"

        if info.get("duration_sec", 0) > max_duration_sec:
            return False, f"音频时长超过限制 ({max_duration_sec}秒)"

        return True, ""

    except Exception as e:
        return False, f"验证失败: {e}"
