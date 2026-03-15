"""
适配器管理器 - 统一管理所有平台的消息轮询和处理
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass

from config import get_config
from core import process_voice, process_text
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class AdapterConfig:
    """适配器配置"""
    name: str
    enabled: bool
    config: Dict[str, Any]
    poll_interval: int = 5  # 轮询间隔（秒）


class AdapterManager:
    """
    适配器管理器
    统一管理所有平台的消息接收和发送
    """

    def __init__(self):
        self.config = get_config()
        self.adapters: Dict[str, Any] = {}
        self.running = False
        self.threads: List[threading.Thread] = []
        self.message_handlers: List[Callable] = []

    def register_adapter(self, name: str, adapter_instance: Any, poll_interval: int = 5):
        """
        注册适配器

        Args:
            name: 适配器名称
            adapter_instance: 适配器实例
            poll_interval: 轮询间隔（秒）
        """
        self.adapters[name] = {
            "instance": adapter_instance,
            "poll_interval": poll_interval,
            "last_update_id": 0
        }
        logger.info(f"适配器已注册: {name}")

    def init_adapters(self):
        """初始化所有启用的适配器"""
        adapters_config = getattr(self.config, 'adapters', {})

        # Telegram
        if adapters_config.get('telegram', {}).get('enabled'):
            from adapters.telegram import TelegramAdapter
            config = adapters_config['telegram']
            adapter = TelegramAdapter(config)
            self.register_adapter('telegram', adapter, poll_interval=config.get('poll_interval', 5))
            logger.info("Telegram 适配器已初始化")

        # QQ
        if adapters_config.get('qq', {}).get('enabled'):
            from adapters.qq import QQAdapter
            config = adapters_config['qq']
            adapter = QQAdapter(config)
            self.register_adapter('qq', adapter, poll_interval=config.get('poll_interval', 5))
            logger.info("QQ 适配器已初始化")

        # 企业微信
        if adapters_config.get('wecom', {}).get('enabled'):
            from adapters.wecom import WeComAdapter
            config = adapters_config['wecom']
            adapter = WeComAdapter(config)
            self.register_adapter('wecom', adapter, poll_interval=config.get('poll_interval', 5))
            logger.info("企业微信适配器已初始化")

        # 钉钉
        if adapters_config.get('dingtalk', {}).get('enabled'):
            from adapters.dingtalk import DingTalkAdapter
            config = adapters_config['dingtalk']
            adapter = DingTalkAdapter(config)
            self.register_adapter('dingtalk', adapter, poll_interval=config.get('poll_interval', 5))
            logger.info("钉钉适配器已初始化")

        # 飞书
        if adapters_config.get('feishu', {}).get('enabled'):
            from adapters.feishu import FeishuAdapter
            config = adapters_config['feishu']
            adapter = FeishuAdapter(config)
            self.register_adapter('feishu', adapter, poll_interval=config.get('poll_interval', 5))
            logger.info("飞书适配器已初始化")

        # WhatsApp
        if adapters_config.get('whatsapp', {}).get('enabled'):
            from adapters.whatsapp import WhatsAppAdapter
            config = adapters_config['whatsapp']
            adapter = WhatsAppAdapter(config)
            self.register_adapter('whatsapp', adapter, poll_interval=config.get('poll_interval', 5))
            logger.info("WhatsApp 适配器已初始化")

        logger.info(f"共初始化 {len(self.adapters)} 个适配器")

    def process_message(self, adapter_name: str, message: Any):
        """
        处理收到的消息

        Args:
            adapter_name: 适配器名称
            message: 消息对象
        """
        from adapters.base import Message

        if not isinstance(message, Message):
            logger.warning(f"未知消息类型: {type(message)}")
            return

        logger.info(f"[{adapter_name}] 收到消息 from {message.user.name or message.user.id}")

        try:
            # 处理语音消息
            if message.voice_url or message.voice_file:
                logger.info(f"[{adapter_name}] 处理语音消息...")

                # 下载语音文件
                adapter = self.adapters[adapter_name]["instance"]
                voice_file = message.voice_file

                if not voice_file and message.voice_url:
                    # 需要下载语音
                    voice_file = adapter.download_voice(message.voice_url)

                if not voice_file:
                    logger.error(f"[{adapter_name}] 语音下载失败")
                    adapter.send_text(message.chat_id, "语音下载失败，请重试")
                    return

                # 语音识别 + 生成回复
                result = process_voice(voice_file)

                if not result.get("success"):
                    error_msg = result.get("error", "处理失败")
                    logger.error(f"[{adapter_name}] 处理失败: {error_msg}")
                    adapter.send_text(message.chat_id, f"处理失败: {error_msg}")
                    return

                # 发送识别结果
                recognized_text = result.get("recognized_text", "")
                reply_text = result.get("reply_text", "")
                reply_voice = result.get("reply_voice")

                # 发送文本回复
                if reply_text:
                    adapter.send_text(
                        message.chat_id,
                        f"🎤 识别: {recognized_text}\n🤖 回复: {reply_text}"
                    )

                # 发送语音回复
                if reply_voice and Path(reply_voice).exists():
                    adapter.send_voice(message.chat_id, reply_voice)

            # 处理文本消息
            elif message.text:
                logger.info(f"[{adapter_name}] 处理文本消息: {message.text}")

                result = process_text(message.text)

                if not result.get("success"):
                    error_msg = result.get("error", "处理失败")
                    adapter.send_text(message.chat_id, f"处理失败: {error_msg}")
                    return

                reply_text = result.get("reply_text", "")
                reply_voice = result.get("reply_voice")

                # 发送文本回复
                if reply_text:
                    adapter.send_text(message.chat_id, reply_text)

                # 发送语音回复
                if reply_voice and Path(reply_voice).exists():
                    adapter = self.adapters[adapter_name]["instance"]
                    adapter.send_voice(message.chat_id, reply_voice)

        except Exception as e:
            logger.error(f"[{adapter_name}] 处理消息失败: {e}")
            try:
                adapter = self.adapters[adapter_name]["instance"]
                adapter.send_text(message.chat_id, f"处理出错: {str(e)}")
            except:
                pass

    def _poll_telegram(self, adapter_info: dict):
        """轮询 Telegram 消息"""
        adapter = adapter_info["instance"]
        poll_interval = adapter_info["poll_interval"]
        last_update_id = adapter_info.get("last_update_id", 0)

        while self.running:
            try:
                updates = adapter.get_updates(offset=last_update_id + 1, limit=10)

                for update in updates:
                    update_id = update.get("update_id")
                    if update_id:
                        last_update_id = max(last_update_id, update_id)
                        adapter_info["last_update_id"] = last_update_id

                    # 解析消息
                    message = adapter.parse_webhook(update)
                    if message:
                        self.process_message("telegram", message)

                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"[telegram] 轮询错误: {e}")
                time.sleep(poll_interval)

    def _poll_qq(self, adapter_info: dict):
        """轮询 QQ 消息"""
        adapter = adapter_info["instance"]
        poll_interval = adapter_info["poll_interval"]

        while self.running:
            try:
                # QQ Bot 使用 WebSocket 或主动轮询
                # 这里使用轮询方式获取消息
                messages = adapter.get_messages(limit=10)

                for msg in messages:
                    message = adapter.parse_message(msg)
                    if message:
                        self.process_message("qq", message)

                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"[qq] 轮询错误: {e}")
                time.sleep(poll_interval)

    def _poll_generic(self, adapter_name: str, adapter_info: dict):
        """通用轮询（用于企业微信、钉钉、飞书等）"""
        adapter = adapter_info["instance"]
        poll_interval = adapter_info["poll_interval"]

        while self.running:
            try:
                # 各适配器实现 get_messages 方法
                if hasattr(adapter, 'get_messages'):
                    messages = adapter.get_messages(limit=10)

                    for msg in messages:
                        if hasattr(adapter, 'parse_message'):
                            message = adapter.parse_message(msg)
                        else:
                            message = adapter.parse_webhook(msg)

                        if message:
                            self.process_message(adapter_name, message)

                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"[{adapter_name}] 轮询错误: {e}")
                time.sleep(poll_interval)

    def start(self):
        """启动所有适配器轮询"""
        if not self.adapters:
            logger.warning("没有可用的适配器")
            return

        self.running = True
        logger.info("启动适配器管理器...")

        for name, adapter_info in self.adapters.items():
            if name == "telegram":
                thread = threading.Thread(
                    target=self._poll_telegram,
                    args=(adapter_info,),
                    daemon=True
                )
            elif name == "qq":
                thread = threading.Thread(
                    target=self._poll_qq,
                    args=(adapter_info,),
                    daemon=True
                )
            else:
                thread = threading.Thread(
                    target=self._poll_generic,
                    args=(name, adapter_info),
                    daemon=True
                )

            thread.start()
            self.threads.append(thread)
            logger.info(f"[{name}] 轮询线程已启动")

        logger.info(f"所有适配器已启动，共 {len(self.threads)} 个线程")

    def stop(self):
        """停止所有适配器"""
        self.running = False
        logger.info("停止适配器管理器...")

        for thread in self.threads:
            thread.join(timeout=5)

        logger.info("适配器管理器已停止")

    def run_forever(self):
        """持续运行（阻塞）"""
        self.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        finally:
            self.stop()


# 全局管理器实例
_manager: Optional[AdapterManager] = None


def get_manager() -> AdapterManager:
    """获取全局适配器管理器"""
    global _manager
    if _manager is None:
        _manager = AdapterManager()
    return _manager


def start_adapters():
    """启动所有适配器（便捷函数）"""
    manager = get_manager()
    manager.init_adapters()
    manager.run_forever()


if __name__ == "__main__":
    # 测试运行
    start_adapters()
