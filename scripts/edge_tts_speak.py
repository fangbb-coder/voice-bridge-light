#!/usr/bin/env python3
"""
Voice Bridge Piper TTS 语音合成 - 兼容 Edge TTS 接口
用于替换原有的 edge-tts 调用
"""

import sys
import os
import argparse
import shutil
from pathlib import Path

# 添加 Voice Bridge 到路径
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from core import tts

# 语音名称映射（兼容旧版 edge-tts 名称）
VOICE_MAP = {
    # 标准名称
    "zh_CN": "zh_CN",
    "en_US": "en_US",
    "en_US_low": "en_US_low",
    # 兼容 edge-tts 旧名称
    "xiaoxiao": "zh_CN",
    "xiaoyi": "zh_CN",
    "yunjian": "zh_CN",
    "yunxi": "zh_CN",
    "xiaochen": "zh_CN",
    "xiaohan": "zh_CN",
    "xiaomeng": "zh_CN",
    "xiaomo": "zh_CN",
    "xiaoxuan": "zh_CN",
    "xiaoyou": "zh_CN",
    "xiaozhen": "zh_CN",
    "en": "en_US",
    "en_low": "en_US_low",
}


def main():
    parser = argparse.ArgumentParser(description="Voice Bridge Piper TTS")
    parser.add_argument("text", help="要合成的文本")
    parser.add_argument("-o", "--output", default="output.wav", help="输出文件路径")
    parser.add_argument("-v", "--voice", default="zh_CN", help="语音名称 (zh_CN/en_US/en_US_low)")
    parser.add_argument("--speed", type=float, default=1.0, help="语速 (0.5-2.0)")

    args = parser.parse_args()

    # 映射语音名称
    voice_id = VOICE_MAP.get(args.voice, args.voice)
    if voice_id not in ["zh_CN", "en_US", "en_US_low"]:
        print(f"警告: 未知语音 '{args.voice}'，使用默认中文语音")
        voice_id = "zh_CN"

    try:
        # 调用 Voice Bridge TTS
        result = tts(args.text, voice=voice_id)

        if result and Path(result).exists():
            # 复制到指定输出路径
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result, output_path)
            print(f"语音合成完成: {output_path}")
            return 0
        else:
            print("错误: 语音合成失败")
            return 1

    except Exception as e:
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
