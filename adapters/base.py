"""
适配器基类 - 定义统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, BinaryIO
from pathlib import Path


@dataclass
class User:
    """用户信息"""
    id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    extra: Dict[str, Any] = None


@dataclass
class Message:
    """消息对象"""
    id: str
    user: User
    text: Optional[str] = None
    voice_url: Optional[str] = None
    voice_file: Optional[str] = None
    chat_id: Optional[str] = None
    timestamp: Optional[float] = None
    extra: Dict[str, Any] = None


class BaseAdapter(ABC):
    """适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化适配器

        Args:
            config: 配置字典，包含 token, webhook_secret 等
        """
        self.config = config
        self.token = config.get("token")
        self.webhook_secret = config.get("webhook_secret")
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.extra = config.get("extra", {})

    @abstractmethod
    def download_voice(self, file_id: str) -> Optional[str]:
        """
        下载语音文件

        Args:
            file_id: 文件 ID

        Returns:
            本地文件路径
        """
        pass

    @abstractmethod
    def send_voice(self, chat_id: str, file_path: str) -> bool:
        """
        发送语音消息

        Args:
            chat_id: 聊天 ID
            file_path: 语音文件路径

        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    def send_text(self, chat_id: str, text: str) -> bool:
        """
        发送文本消息

        Args:
            chat_id: 聊天 ID
            text: 文本内容

        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    def parse_webhook(self, data: Dict[str, Any]) -> Optional[Message]:
        """
        解析 Webhook 数据

        Args:
            data: Webhook 请求数据

        Returns:
            Message 对象
        """
        pass

    def verify_webhook(self, signature: str, body: bytes) -> bool:
        """
        验证 Webhook 签名

        Args:
            signature: 签名
            body: 请求体

        Returns:
            是否验证通过
        """
        # 默认不验证，子类可重写
        return True

    def is_voice_message(self, message: Message) -> bool:
        """
        检查是否为语音消息

        Args:
            message: 消息对象

        Returns:
            是否为语音消息
        """
        return message.voice_url is not None or message.voice_file is not None

    def get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名"""
        return Path(file_path).suffix.lower()
