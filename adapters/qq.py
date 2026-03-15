"""
QQ 适配器 (基于 QQ Bot API)
支持轮询和 Webhook 两种方式
"""

import requests
import time
from typing import Optional, Dict, Any, List
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
        self.session_id = None
        self.ws_url = None

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

    def get_gateway(self) -> Optional[str]:
        """获取 WebSocket 网关地址"""
        result = self._make_request("GET", "/gateway")
        if result:
            self.ws_url = result.get("url")
            return self.ws_url
        return None

    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取消息（轮询方式）
        QQ Bot 官方推荐使用 WebSocket，但也可以通过主动拉取

        Returns:
            消息列表
        """
        # QQ Bot 需要通过 WebSocket 接收消息
        # 这里返回空列表，实际使用 WebSocket 方式
        return []

    def download_voice(self, file_id: str) -> Optional[str]:
        """
        下载语音文件

        Args:
            file_id: 文件 ID 或 URL

        Returns:
            本地文件路径
        """
        try:
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 如果是 URL，直接下载
            if file_id.startswith("http"):
                response = requests.get(file_id, timeout=30)
                response.raise_for_status()

                file_path = temp_dir / f"qq_voice_{int(time.time())}.silk"
                with open(file_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"语音下载完成: {file_path}")
                return str(file_path)

            # 否则通过 API 获取
            result = self._make_request("GET", f"/channels/{file_id}")
            if not result:
                return None

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
            from pathlib import Path

            path = Path(file_path)
            if not path.exists():
                logger.error(f"语音文件不存在: {file_path}")
                return False

            # QQ Bot 发送语音需要通过富媒体接口
            # 先上传文件
            upload_url = f"{self.API_BASE}/channels/{chat_id}/messages"

            headers = {
                "Authorization": f"QQBot {self.token}",
                "X-Union-Appid": self.bot_app_id
            }

            with open(file_path, "rb") as f:
                files = {"file": (path.name, f, "audio/wav")}
                data = {"msg_type": "7"}  # 语音消息类型

                response = requests.post(upload_url, headers=headers, files=files, data=data, timeout=60)

                if response.status_code == 200:
                    logger.info(f"语音发送成功: {chat_id}")
                    return True
                else:
                    logger.error(f"语音发送失败: {response.text}")
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
        try:
            data = {
                "content": text,
                "msg_type": 0  # 文本消息
            }

            result = self._make_request("POST", f"/channels/{chat_id}/messages", json=data)
            if result:
                logger.info(f"文本发送成功: {chat_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"发送文本失败: {e}")
            return False

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """
        解析消息数据

        Args:
            data: 消息数据

        Returns:
            Message 对象
        """
        try:
            # WebSocket 消息格式
            event = data.get("event", data)
            msg_type = event.get("message_type") or event.get("t")

            # 处理私聊和群消息
            if msg_type not in ["C2C_MESSAGE_CREATE", "GROUP_AT_MESSAGE_CREATE", "AT_MESSAGE_CREATE"]:
                return None

            message = event.get("message", event.get("d", {}).get("message", {}))
            author = event.get("author", event.get("d", {}).get("author", {}))

            msg_id = message.get("id")
            chat_id = event.get("channel_id") or event.get("group_id") or event.get("d", {}).get("channel_id")
            content = message.get("content", "")
            attachments = message.get("attachments", [])

            user = User(
                id=author.get("id", ""),
                name=author.get("username", "")
            )

            text = content
            voice_url = None

            # 检查附件（语音）
            for attachment in attachments:
                content_type = attachment.get("content_type", "")
                if "audio" in content_type or "voice" in content_type:
                    voice_url = attachment.get("url")
                    break

            return Message(
                id=msg_id or str(int(time.time())),
                user=user,
                text=text,
                voice_url=voice_url,
                chat_id=chat_id,
                timestamp=int(time.time()),
                extra={"raw": data}
            )

        except Exception as e:
            logger.error(f"解析消息失败: {e}")
            return None

    def parse_webhook(self, data: Dict[str, Any]) -> Optional[Message]:
        """
        解析 Webhook 数据

        Args:
            data: Webhook 请求数据

        Returns:
            Message 对象
        """
        return self.parse_message(data)

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
