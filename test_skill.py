#!/usr/bin/env python3
"""
Voice Bridge - 部署前测试脚本
验证代码语法、导入和基本功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("测试模块导入...")
    print("=" * 60)
    
    errors = []
    
    # 测试基础模块
    try:
        from config import get_config, reload_config
        print("✅ config 模块导入成功")
    except Exception as e:
        errors.append(f"❌ config 模块导入失败: {e}")
    
    try:
        from utils.logger import setup_logger
        print("✅ utils.logger 模块导入成功")
    except Exception as e:
        errors.append(f"❌ utils.logger 模块导入失败: {e}")
    
    # 测试语音模块
    try:
        from voice.audio_utils import convert_to_wav, cleanup_temp_files
        print("✅ voice.audio_utils 模块导入成功")
    except Exception as e:
        errors.append(f"❌ voice.audio_utils 模块导入失败: {e}")
    
    try:
        from voice.asr_whisper import WhisperASR
        print("✅ voice.asr_whisper 模块导入成功")
    except Exception as e:
        errors.append(f"❌ voice.asr_whisper 模块导入失败: {e}")
    
    try:
        from voice.tts_piper import PiperTTS
        print("✅ voice.tts_piper 模块导入成功")
    except Exception as e:
        errors.append(f"❌ voice.tts_piper 模块导入失败: {e}")
    
    # 测试助手模块
    try:
        from assistant.voice_assistant import VoiceAssistant
        print("✅ assistant.voice_assistant 模块导入成功")
    except Exception as e:
        errors.append(f"❌ assistant.voice_assistant 模块导入失败: {e}")
    
    # 测试适配器模块
    try:
        from adapters import get_adapter, list_adapters, BaseAdapter
        print("✅ adapters 模块导入成功")
    except Exception as e:
        errors.append(f"❌ adapters 模块导入失败: {e}")
    
    # 测试 FastAPI 相关
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        print("✅ FastAPI 相关模块导入成功")
    except Exception as e:
        errors.append(f"❌ FastAPI 模块导入失败: {e}")
    
    if errors:
        print("\n" + "=" * 60)
        print("导入错误:")
        for err in errors:
            print(err)
        return False
    
    print("\n✅ 所有模块导入成功!")
    return True


def test_config():
    """测试配置加载"""
    print("\n" + "=" * 60)
    print("测试配置加载...")
    print("=" * 60)
    
    try:
        from config import get_config
        config = get_config()
        print(f"✅ 配置加载成功")
        print(f"   语言: {config.language}")
        print(f"   唤醒词: {config.wake_word}")
        print(f"   自动语音回复: {config.auto_voice_reply}")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def test_logger():
    """测试日志系统"""
    print("\n" + "=" * 60)
    print("测试日志系统...")
    print("=" * 60)
    
    try:
        from utils.logger import setup_logger
        logger = setup_logger("test")
        logger.info("测试日志消息")
        print("✅ 日志系统正常工作")
        return True
    except Exception as e:
        print(f"❌ 日志系统测试失败: {e}")
        return False


def test_asr_class():
    """测试 ASR 类（不加载模型）"""
    print("\n" + "=" * 60)
    print("测试 ASR 类...")
    print("=" * 60)
    
    try:
        from voice.asr_whisper import WhisperASR
        
        # 测试类属性
        print(f"✅ 支持的模型大小: {list(WhisperASR.MODEL_SIZES.keys())}")
        print(f"✅ base 模型大小: {WhisperASR.MODEL_SIZES['base']}MB")
        
        # 测试实例化（不加载模型）
        # 注意：这里会尝试加载模型，如果模型不存在会警告但不报错
        print("✅ ASR 类定义正确")
        return True
    except Exception as e:
        print(f"❌ ASR 类测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tts_class():
    """测试 TTS 类"""
    print("\n" + "=" * 60)
    print("测试 TTS 类...")
    print("=" * 60)
    
    try:
        from voice.tts_piper import PiperTTS
        
        # 测试类属性
        print(f"✅ 支持的模型: {list(PiperTTS.MODELS.keys())}")
        for lang, info in PiperTTS.MODELS.items():
            print(f"   - {lang}: {info['name']} ({info['size_mb']}MB)")
        
        # 测试模型路径检查
        tts = PiperTTS.__new__(PiperTTS)
        tts.model_dir = Path("models/piper")
        print("✅ TTS 类定义正确")
        return True
    except Exception as e:
        print(f"❌ TTS 类测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adapters():
    """测试适配器系统"""
    print("\n" + "=" * 60)
    print("测试适配器系统...")
    print("=" * 60)
    
    try:
        from adapters import list_adapters
        adapters = list_adapters()
        print(f"✅ 发现 {len(adapters)} 个适配器:")
        for name in adapters:
            print(f"   - {name}")
        return True
    except Exception as e:
        print(f"❌ 适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_syntax_check():
    """语法检查"""
    print("\n" + "=" * 60)
    print("语法检查...")
    print("=" * 60)
    
    import py_compile
    
    files_to_check = [
        "core.py",
        "config.py",
        "voice/asr_whisper.py",
        "voice/tts_piper.py",
        "voice/audio_utils.py",
        "assistant/voice_assistant.py",
        "adapters/__init__.py",
        "adapters/base.py",
        "adapters/manager.py",
        "utils/logger.py",
    ]
    
    errors = []
    for file in files_to_check:
        try:
            py_compile.compile(file, doraise=True)
            print(f"✅ {file}")
        except Exception as e:
            errors.append(f"❌ {file}: {e}")
    
    if errors:
        print("\n语法错误:")
        for err in errors:
            print(err)
        return False
    
    print("\n✅ 所有文件语法正确!")
    return True


def test_requirements():
    """检查依赖"""
    print("\n" + "=" * 60)
    print("检查依赖...")
    print("=" * 60)
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "numpy",
        "soundfile",
        "pydub",
        "pyyaml",
        "requests",
    ]
    
    optional_packages = [
        "openai-whisper",
        "piper-tts",
    ]
    
    errors = []
    warnings = []
    
    for pkg in required_packages:
        try:
            import_name = pkg.replace('-', '_')
            if pkg == "pyyaml":
                import_name = "yaml"
            __import__(import_name)
            print(f"✅ {pkg}")
        except ImportError:
            errors.append(f"❌ {pkg} (必需)")
    
    for pkg in optional_packages:
        try:
            if pkg == "openai-whisper":
                import whisper
                print(f"✅ {pkg}")
            elif pkg == "piper-tts":
                import piper
                print(f"✅ {pkg}")
            else:
                __import__(pkg.replace('-', '_'))
                print(f"✅ {pkg}")
        except ImportError:
            warnings.append(f"⚠️  {pkg} (可选，用于语音功能)")
    
    if warnings:
        print("\n可选依赖缺失:")
        for warn in warnings:
            print(warn)
    
    if errors:
        print("\n必需依赖缺失:")
        for err in errors:
            print(err)
        return False
    
    print("\n✅ 所有必需依赖已安装!")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Voice Bridge - 部署前测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("语法检查", test_syntax_check()))
    results.append(("模块导入", test_imports()))
    results.append(("依赖检查", test_requirements()))
    results.append(("配置加载", test_config()))
    results.append(("日志系统", test_logger()))
    results.append(("ASR 类", test_asr_class()))
    results.append(("TTS 类", test_tts_class()))
    results.append(("适配器系统", test_adapters()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 所有测试通过! 代码可以部署。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请修复后再部署。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
