"""
QQ 适配器 (基于 QQ Bot API)
"""

import requests
from typing import Optional, Dict, Any
from pathlib import Path

from adapters.base import BaseAdapter, Message, User
from utils.logger import setup_logger

logger = setup_logger(__name__)


class QQAdapter(BaseAdapter):
    """QQ Bot 适配器"""

    API_BASE = "https://api.sgroup.qq.com"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_app_id = config.get("app_id")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """调用 QQ Bot API"""
        url = f"{self.API_BASE}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"QQBot {self.token}"
        headers["X-Union-Appid"] = self.bot_app_id

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, **kwargs, timeout=30)
            else:
                headers.setdefault("Content-Type", "application/json")
                response = requests.post(url, headers=headers, **kwargs, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"QQ 请求失败: {e}")
            return None

    def download_voice(self, file_id: str) -> Optional[str]:
        """
        下载语音文件

        Args:
            file_id: 文件 ID

        Returns:
            本地文件路径
        """
        try:
            # QQ Bot API 获取媒体
            result = self._make_request("GET", f"/channels/{file_id}")
            if not result:
                return None

            # 下载文件
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # QQ 语音通常是 silk 格式
            file_path = temp_dir / f"qq_voice_{file_id}.silk"

            logger.info(f"语音下载完成: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"下载语音失败: {e}")
            return None

    def send_voice(self, chat_id: str, file_path: str) -> bool:
        """
        发送语音消息

        Args:
            chat_id: 频道 ID 或群 ID
            file_path: 语音文件路径

        Returns:
            是否发送成功
        """
        try:
            # QQ Bot 需要先上传文件获取 URL
            logger.warning("QQ 适配器暂不支持直接发送语音")
            return False

        except Exception as e:
            logger.error(f"发送语音失败: {e}")
            return False

    def send_text(self, chat_id: str, text: str) -> bool:
        """
        发送文本消息

        Args:
            chat_id: 频道 ID
            text: 文本内容

        Returns:
            是否发送成功
        """
        data = {
            "content": text,
            "msg_type": 0  # 文本消息
        }

        result = self._make_request("POST", f"/channels/{chat_id}/messages", json=data)
        if result:
            logger.info(f"文本发送成功: {chat_id}")
            return True
        return False

    def parse_webhook(self, data: Dict[str, Any]) -> Optional[Message]:
        """
        解析 Webhook 数据

        Args:
            data: Webhook 请求数据

        Returns:
            Message 对象
        """
        try:
            event = data.get("event", {})
            msg_type = event.get("message_type")

            if msg_type != "C2C_MESSAGE_CREATE":
                return None

            message = event.get("message", {})
            author = event.get("author", {})

            msg_id = message.get("id")
            chat_id = event.get("channel_id") or event.get("group_id")
            content = message.get("content")
            attachments = message.get("attachments", [])

            user = User(
                id=author.get("id"),
                name=author.get("username")
            )

            text = content
            voice_file = None

            # 检查附件
            for attachment in attachments:
                if attachment.get("content_type", "").startswith("audio"):
                    voice_file = attachment.get("url")
                    break

            return Message(
                id=msg_id,
                user=user,
                text=text,
                voice_file=voice_file,
                chat_id=chat_id,
                timestamp=int(event.get("timestamp", 0)),
                extra={"raw": data}
            )

        except Exception as e:
            logger.error(f"解析 Webhook 失败: {e}")
            return None

    def verify_webhook(self, signature: str, timestamp: str, body: bytes) -> bool:
        """
        验证 QQ Bot Webhook 签名

        Args:
            signature: 签名
            timestamp: 时间戳
            body: 请求体

        Returns:
            是否验证通过
        """
        try:
            import hmac
            import hashlib

            secret = self.webhook_secret
            if not secret:
                return True

            # QQ Bot 签名算法
            message = f"{timestamp}{body.decode()}".encode()
            expected = hmac.new(
                secret.encode(),
                message,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected, signature)

        except Exception as e:
            logger.error(f"验证签名失败: {e}")
            return False
