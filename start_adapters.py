#!/usr/bin/env python3
"""
Voice Bridge - 启动所有适配器
后台持续运行，自动处理各平台消息
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from adapters.manager import start_adapters

if __name__ == "__main__":
    print("=" * 60)
    print("Voice Bridge - 适配器管理器")
    print("=" * 60)
    print("支持平台: Telegram, QQ, 企业微信, 钉钉, 飞书, WhatsApp")
    print("功能: 自动接收语音/文本消息，语音识别，语音合成，自动回复")
    print("=" * 60)
    print()

    start_adapters()
