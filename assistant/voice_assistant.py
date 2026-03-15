import datetime
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from voice.asr import VoiceASR
from voice.tts import VoiceTTS
from voice.audio_utils import generate_temp_path, cleanup_temp_files
from config import get_config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class VoiceAssistant:
    """语音助手核心类"""

    def __init__(self, asr: VoiceASR, tts: VoiceTTS):
        """
        初始化语音助手

        Args:
            asr: 语音识别器
            tts: 语音合成器
        """
        self.asr = asr
        self.tts = tts
        self.config = get_config()

        # 命令处理器映射
        self.command_handlers: Dict[str, Callable[[str], str]] = {
            "hello": self._handle_hello,
            "你好": self._handle_hello,
            "time": self._handle_time,
            "时间": self._handle_time,
            "date": self._handle_date,
            "日期": self._handle_date,
            "help": self._handle_help,
            "帮助": self._handle_help,
        }

    def process(self, text: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        处理用户输入并生成回复

        Args:
            text: 用户输入文本

        Returns:
            包含文本回复和语音文件路径的字典
        """
        if not text:
            logger.debug("输入文本为空")
            return None

        text = text.strip()
        logger.info(f"处理输入: {text}")

        try:
            # 生成回复文本
            reply = self.generate_reply(text)

            # 合成语音
            voice_path = None
            if self.config.auto_voice_reply:
                voice_path = self._synthesize_reply(reply)

            # 清理旧临时文件
            cleanup_temp_files(self.config.temp_dir, self.config.max_temp_files)

            return {
                "text": reply,
                "voice": voice_path
            }

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return {
                "text": "抱歉，处理您的消息时出现了错误。",
                "voice": None
            }

    def generate_reply(self, text: str) -> str:
        """
        根据输入生成回复

        Args:
            text: 用户输入

        Returns:
            回复文本
        """
        text_lower = text.lower()

        # 检查唤醒词
        wake_word = self.config.wake_word.lower()
        if wake_word and wake_word in text_lower:
            return self._handle_wakeup()

        # 检查命令
        for keyword, handler in self.command_handlers.items():
            if keyword in text_lower:
                return handler(text)

        # 默认回复
        return self._handle_default(text)

    def _synthesize_reply(self, reply: str) -> Optional[str]:
        """
        将回复合成为语音

        Args:
            reply: 回复文本

        Returns:
            语音文件路径
        """
        try:
            output_path = generate_temp_path(
                self.config.temp_dir,
                suffix="_reply.wav"
            )

            voice_path = self.tts.synthesize(
                text=reply,
                output=output_path,
                speed=self.config.tts.speed
            )

            return voice_path

        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return None

    # ========== 命令处理器 ==========

    def _handle_hello(self, text: str) -> str:
        """处理问候"""
        greetings = {
            "zh": "你好！我是你的语音助手，有什么可以帮你的吗？",
            "en": "Hello! I'm your voice assistant. How can I help you?"
        }
        return greetings.get(self.config.language, greetings["zh"])

    def _handle_time(self, text: str) -> str:
        """处理时间查询"""
        now = datetime.datetime.now()

        if self.config.language == "zh":
            return f"现在是 {now.strftime('%H点%M分')}"
        else:
            return f"The time is {now.strftime('%I:%M %p')}"

    def _handle_date(self, text: str) -> str:
        """处理日期查询"""
        now = datetime.datetime.now()

        if self.config.language == "zh":
            return f"今天是 {now.strftime('%Y年%m月%d日')}，星期{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}"
        else:
            return f"Today is {now.strftime('%A, %B %d, %Y')}"

    def _handle_help(self, text: str) -> str:
        """处理帮助请求"""
        if self.config.language == "zh":
            return (
                "我可以帮你：\n"
                "• 说'你好'或'hello'打招呼\n"
                "• 问'时间'或'time'查询当前时间\n"
                "• 问'日期'或'date'查询今天日期\n"
                "• 直接说话，我会尽力回复你"
            )
        else:
            return (
                "I can help you:\n"
                "• Say 'hello' or '你好' to greet\n"
                "• Ask 'time' for current time\n"
                "• Ask 'date' for today's date\n"
                "• Just talk to me, I'll do my best to respond"
            )

    def _handle_wakeup(self) -> str:
        """处理唤醒词"""
        if self.config.language == "zh":
            return "我在听，请说。"
        else:
            return "I'm listening, please speak."

    def _handle_default(self, text: str) -> str:
        """默认回复"""
        defaults = {
            "zh": f"我收到了你的消息：{text}",
            "en": f"I received your message: {text}"
        }
        return defaults.get(self.config.language, defaults["zh"])

    def add_command_handler(self, keyword: str, handler: Callable[[str], str]) -> None:
        """
        添加自定义命令处理器

        Args:
            keyword: 触发关键词
            handler: 处理函数
        """
        self.command_handlers[keyword] = handler
        logger.info(f"添加命令处理器: {keyword}")

    def is_ready(self) -> bool:
        """检查助手是否就绪"""
        return self.asr.is_ready() and self.tts.is_ready()
