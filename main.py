#!/usr/bin/env python3
"""
Voice Bridge - OpenClaw Skill 入口
提供 TTS/STT 核心功能的 HTTP API 服务
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 从 core 导入所有功能
from core import (
    speech_to_text,
    text_to_speech,
    process_voice,
    process_text,
    health_check,
    core_state
)


def main():
    """主入口函数"""
    # 初始化核心状态
    core_state.init()

    # 健康检查
    health = health_check()
    print(f"Voice Bridge 状态: {health}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
