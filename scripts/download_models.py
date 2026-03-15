#!/usr/bin/env python3
"""
轻量级模型下载脚本
- Whisper ASR (base, 74MB)
- Piper TTS (中文 60MB, 英文 25MB)
"""

import os
import sys
import shutil
import urllib.request
from pathlib import Path

# 轻量级模型配置
MODELS = {
    "whisper": {
        "name": "whisper-base",
        "description": "Whisper Base ASR 模型 (74MB)",
        "type": "whisper",
        "size_mb": 74,
        "install_cmd": "whisper --model base --help"
    },
    "piper_zh": {
        "name": "zh_CN-huayan-medium",
        "description": "Piper 中文女声 TTS (60MB)",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json",
        "size_mb": 60,
        "extract_dir": "models/piper"
    },
    "piper_en": {
        "name": "en_US-lessac-low",
        "description": "Piper 英文女声 TTS (25MB)",
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx.json",
        "size_mb": 25,
        "extract_dir": "models/piper"
    }
}


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent


def ensure_dir(path: Path) -> None:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)


def check_disk_space(path: Path, required_mb: int) -> bool:
    """检查磁盘空间"""
    try:
        stat = shutil.disk_usage(path)
        free_mb = stat.free / (1024 * 1024)
        return free_mb >= required_mb
    except Exception as e:
        print(f"检查磁盘空间失败: {e}")
        return False


def download_file(url: str, dest: Path, desc: str = "") -> bool:
    """下载文件"""
    try:
        print(f"\n📥 下载: {desc or url}")
        print(f"   目标: {dest}")

        ensure_dir(dest.parent)

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })

        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(dest, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        print(f"\r   进度: {percent:.1f}% ({mb:.1f}MB/{total_mb:.1f}MB)", end='', flush=True)

        print(f"\n   ✅ 完成")
        return True

    except Exception as e:
        print(f"\n   ❌ 失败: {e}")
        return False


def download_piper_model(model_key: str) -> bool:
    """下载 Piper TTS 模型"""
    config = MODELS[model_key]
    root = get_project_root()

    model_dir = root / config["extract_dir"]
    ensure_dir(model_dir)

    model_name = config["name"]
    model_path = model_dir / f"{model_name}.onnx"
    json_path = model_dir / f"{model_name}.onnx.json"

    # 检查是否已存在
    if model_path.exists() and json_path.exists():
        print(f"✅ {config['description']} 已存在")
        return True

    # 下载模型文件
    if not download_file(config["url"], model_path, config["name"]):
        return False

    # 下载配置文件
    if not download_file(config["json_url"], json_path, f"{model_name}.json"):
        return False

    print(f"✅ {config['description']} 安装完成")
    return True


def setup_whisper() -> bool:
    """设置 Whisper（自动下载模型）"""
    print("\n" + "="*50)
    print("设置 Whisper ASR")
    print("="*50)
    print("Whisper 模型会在首次使用时自动下载")
    print("模型大小: base (74MB)")
    print("模型缓存目录: models/whisper")

    # 创建缓存目录
    root = get_project_root()
    whisper_dir = root / "models" / "whisper"
    ensure_dir(whisper_dir)

    # 设置环境变量
    os.environ["WHISPER_CACHE_DIR"] = str(whisper_dir)

    print("✅ Whisper 配置完成")
    print("   首次运行时会自动下载模型")
    return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="下载轻量级语音模型")
    parser.add_argument(
        "model",
        nargs="?",
        choices=["whisper", "piper_zh", "piper_en", "all"],
        default="all",
        help="要下载的模型"
    )
    parser.add_argument("--force", action="store_true", help="强制重新下载")

    args = parser.parse_args()

    root = get_project_root()

    # 计算所需空间
    if args.model == "all":
        required_mb = sum(m.get("size_mb", 0) for m in MODELS.values())
    else:
        required_mb = MODELS[args.model].get("size_mb", 100)

    print(f"📦 需要磁盘空间: ~{required_mb}MB")

    if not check_disk_space(root, required_mb * 1.5):
        print(f"❌ 磁盘空间不足！")
        return 1

    success = True

    # 下载 Piper 中文模型
    if args.model in ["piper_zh", "all"]:
        if not download_piper_model("piper_zh"):
            success = False

    # 下载 Piper 英文模型
    if args.model in ["piper_en", "all"]:
        if not download_piper_model("piper_en"):
            success = False

    # 设置 Whisper
    if args.model in ["whisper", "all"]:
        if not setup_whisper():
            success = False

    print("\n" + "="*50)
    if success:
        print("✅ 所有模型准备完成！")
        print("="*50)
        print("\n模型信息:")
        print("  - Whisper ASR: base (74MB), 首次运行时自动下载")
        print("  - Piper TTS 中文: huayan-medium (60MB)")
        print("  - Piper TTS 英文: lessac-low (25MB)")
        print("\n现在可以启动服务:")
        print("  python main.py")
        return 0
    else:
        print("❌ 部分模型下载失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
