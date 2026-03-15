#!/usr/bin/env python3
"""
模型下载脚本 - 下载语音助手所需的离线模型
"""

import os
import sys
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

# 模型配置
MODELS = {
    "asr": {
        "name": "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2",
        "md5": None,
        "extract_dir": "models/sherpa-onnx-sense-voice"
    },
    "tts": {
        "name": "kokoro-multi-lang-v1_0",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2",
        "md5": None,
        "extract_dir": "models/kokoro"
    }
}


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent


def ensure_dir(path: Path) -> None:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> bool:
    """
    下载文件并显示进度

    Args:
        url: 下载链接
        dest: 目标路径
        chunk_size: 分块大小

    Returns:
        是否下载成功
    """
    try:
        print(f"正在下载: {url}")
        print(f"目标路径: {dest}")

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        })

        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0

            with open(dest, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)

        print(f"\n下载完成: {dest}")
        return True

    except urllib.error.URLError as e:
        print(f"\n下载失败 (URL错误): {e}")
        return False
    except Exception as e:
        print(f"\n下载失败: {e}")
        return False


def extract_tar_bz2(archive_path: Path, extract_to: Path) -> bool:
    """
    解压 tar.bz2 文件

    Args:
        archive_path: 压缩包路径
        extract_to: 解压目标目录

    Returns:
        是否解压成功
    """
    import tarfile

    try:
        print(f"正在解压: {archive_path}")
        ensure_dir(extract_to)

        with tarfile.open(archive_path, 'r:bz2') as tar:
            tar.extractall(path=extract_to)

        print(f"解压完成: {extract_to}")
        return True

    except Exception as e:
        print(f"解压失败: {e}")
        return False


def verify_model(model_dir: Path, required_files: list) -> bool:
    """
    验证模型目录是否完整

    Args:
        model_dir: 模型目录
        required_files: 必需文件列表

    Returns:
        是否完整
    """
    if not model_dir.exists():
        return False

    for file in required_files:
        if not (model_dir / file).exists():
            return False

    return True


def download_model(model_type: str, force: bool = False) -> bool:
    """
    下载指定类型的模型

    Args:
        model_type: 模型类型 (asr/tts)
        force: 是否强制重新下载

    Returns:
        是否成功
    """
    if model_type not in MODELS:
        print(f"未知模型类型: {model_type}")
        return False

    config = MODELS[model_type]
    root = get_project_root()

    model_dir = root / config["extract_dir"]

    # 检查是否已存在
    if not force and model_dir.exists():
        print(f"模型已存在: {model_dir}")
        print("使用 --force 重新下载")
        return True

    # 创建临时目录
    temp_dir = root / "temp"
    ensure_dir(temp_dir)

    # 下载压缩包
    archive_name = f"{config['name']}.tar.bz2"
    archive_path = temp_dir / archive_name

    if not download_file(config["url"], archive_path):
        return False

    # 解压
    if not extract_tar_bz2(archive_path, model_dir.parent):
        return False

    # 清理压缩包
    try:
        archive_path.unlink()
        print(f"已清理临时文件: {archive_path}")
    except Exception as e:
        print(f"清理临时文件失败: {e}")

    print(f"模型 {model_type} 安装完成: {model_dir}")
    return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="下载语音助手模型")
    parser.add_argument(
        "model",
        nargs="?",
        choices=["asr", "tts", "all"],
        default="all",
        help="要下载的模型 (asr/tts/all)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新下载"
    )

    args = parser.parse_args()

    root = get_project_root()
    models_dir = root / "models"
    ensure_dir(models_dir)

    success = True

    if args.model in ("asr", "all"):
        print("=" * 50)
        print("下载 ASR 模型 (语音识别)")
        print("=" * 50)
        if not download_model("asr", args.force):
            success = False

    if args.model in ("tts", "all"):
        print("\n" + "=" * 50)
        print("下载 TTS 模型 (语音合成)")
        print("=" * 50)
        if not download_model("tts", args.force):
            success = False

    print("\n" + "=" * 50)
    if success:
        print("所有模型下载完成!")
        print(f"模型目录: {models_dir}")
    else:
        print("部分模型下载失败，请检查网络连接")
        sys.exit(1)


if __name__ == "__main__":
    main()
