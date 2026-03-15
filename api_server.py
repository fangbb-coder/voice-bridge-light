#!/usr/bin/env python3
"""
Voice Bridge - Flask HTTP 服务
为 OpenClaw 提供 STT/TTS API 接口
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional
from flask import Flask, request, jsonify, send_file, Form

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core import core_state, speech_to_text, text_to_speech, process_voice, process_text
from utils.logger import setup_logger

logger = setup_logger("api_server")

# 创建 Flask 应用
app = Flask(__name__)

# 初始化核心状态
@app.before_request
def ensure_initialized():
    """确保服务已初始化"""
    if not core_state.initialized:
        logger.info("初始化 Voice Bridge API 服务")
        core_state.init()
        logger.info("Voice Bridge API 服务已就绪")


# ========== API 端点 ==========
@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "initialized": core_state.initialized,
        "asr_ready": core_state.asr.is_ready() if core_state.asr else False,
        "tts_ready": core_state.tts.is_ready() if core_state.tts else False
    })


@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """
    文本转语音
    
    JSON 参数:
    - text: 要合成的文本（必填）
    - voice: 语音类型，默认中文女声 (zh_CN/en_US/en_US_low)
    
    示例:
    {"text": "你好，我是语音助手"}
    {"text": "Hello", "voice": "en_US"}
    """
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        voice = data.get('voice')  # 默认 None，会使用配置中的中文女声
        
        if not text:
            return jsonify({"success": False, "error": "文本不能为空"}), 400
        
        result = text_to_speech(text, voice)
        return jsonify(result)
    except Exception as e:
        logger.error(f"TTS 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/tts/file', methods=['POST'])
def tts_file_endpoint():
    """
    文本转语音，直接返回音频文件
    
    Form 参数:
    - text: 要合成的文本（必填）
    - voice: 语音类型，默认中文女声 (zh_CN/en_US/en_US_low)
    """
    try:
        text = request.form.get('text', '')
        voice = request.form.get('voice')  # 默认 None，使用配置中的中文女声
        
        if not text:
            return jsonify({"success": False, "error": "文本不能为空"}), 400
        
        result = text_to_speech(text, voice)
        if result.get("success") and result.get("audio_file"):
            audio_path = result["audio_file"]
            return send_file(audio_path, mimetype="audio/wav", as_attachment=True, download_name="speech.wav")
        else:
            return jsonify({"success": False, "error": result.get("error", "合成失败")}), 500
    except Exception as e:
        logger.error(f"TTS 文件生成失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/stt', methods=['POST'])
def stt_endpoint():
    """
    语音转文本
    
    Form 参数:
    - audio: 音频文件 (wav/mp3/ogg)
    - language: 语言代码 (zh/en/ja/ko)
    """
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "缺少音频文件"}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'zh')
        
        # 保存上传的文件
        suffix = Path(audio_file.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            audio_file.save(tmp)
            tmp_path = tmp.name
        
        try:
            # 调用 STT
            result = speech_to_text(tmp_path, language)
            return jsonify(result)
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        logger.error(f"STT 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/audio/transcriptions', methods=['POST'])
def transcribe_openai():
    """
    OpenAI 兼容的语音转文本接口
    
    OpenClaw QQBot 使用此接口格式
    
    Form 参数:
    - file: 音频文件 (OpenAI 标准参数名)
    - audio: 音频文件 (兼容参数名)
    - language: 语言代码 (可选)
    """
    try:
        # 获取音频文件（支持多种参数名）
        audio_file = None
        if 'file' in request.files:
            audio_file = request.files['file']
        elif 'audio' in request.files:
            audio_file = request.files['audio']
        
        if not audio_file:
            logger.error("缺少音频文件")
            return jsonify({"error": "No audio file provided"}), 400
        
        language = request.form.get('language', 'zh')
        
        # 保存临时文件
        suffix = Path(audio_file.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            audio_file.save(tmp)
            tmp_path = tmp.name
        
        try:
            # 调用 STT
            logger.info(f"识别音频: {tmp_path}")
            result = speech_to_text(tmp_path, language)
            
            if result.get('success') and result.get('text'):
                text = result['text']
                logger.info(f"识别结果: {text}")
                
                # OpenAI 兼容响应格式
                return jsonify({
                    "text": text,
                    "task": "transcribe",
                    "language": language,
                    "duration": 0,
                    "words": []
                })
            else:
                error_msg = result.get('error', 'Transcription failed')
                logger.error(f"识别失败: {error_msg}")
                return jsonify({"error": error_msg}), 500
                
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        logger.error(f"识别失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/process/text', methods=['POST'])
def process_text_endpoint():
    """
    处理文本消息
    
    JSON 参数:
    - text: 用户输入的文本
    - reply_with_voice: 是否用语音回复
    """
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        reply_with_voice = data.get('reply_with_voice', True)
        
        if not text:
            return jsonify({"success": False, "error": "文本不能为空"}), 400
        
        result = process_text(text, reply_with_voice)
        return jsonify(result)
    except Exception as e:
        logger.error(f"处理文本失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/process/voice', methods=['POST'])
def process_voice_endpoint():
    """
    处理语音消息（识别 + 回复）
    
    Form 参数:
    - audio: 音频文件
    - language: 语言代码
    
    返回回复语音文件
    """
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "缺少音频文件"}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'zh')
        
        # 保存上传的文件
        suffix = Path(audio_file.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            audio_file.save(tmp)
            tmp_path = tmp.name
        
        try:
            # 处理语音
            result = process_voice(tmp_path, language)
            
            if result.get("success") and result.get("reply_voice"):
                # 返回回复语音文件
                return send_file(
                    result["reply_voice"],
                    mimetype="audio/wav",
                    as_attachment=True,
                    download_name="reply.wav"
                )
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "处理失败")
                }), 500
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        logger.error(f"处理语音失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ========== 主入口 ==========
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Bridge API Server")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=18790, help="端口")
    
    args = parser.parse_args()
    
    logger.info(f"启动 API 服务: {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)
