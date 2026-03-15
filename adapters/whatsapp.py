"""
WhatsApp 适配器 (基于 WhatsApp Business API)
"""

import requests
from typing import Optional, Dict, Any, List
from pathlib import Path

from adapters.base import BaseAdapter, Message, User
from utils.logger import setup_logger

logger = setup_logger(__name__)


class WhatsAppAdapter(BaseAdapter):
    """WhatsApp Business API 适配器"""

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.phone_number_id = config.get("extra", {}).get("phone_number_id")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """调用 WhatsApp API"""
        url = f"{self.API_BASE}/{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, **kwargs, timeout=30)
            else:
                headers.setdefault("Content-Type", "application/json")
                response = requests.post(url, headers=headers, **kwargs, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"WhatsApp 请求失败: {e}")
            return None

    def download_voice(self, media_id: str) -> Optional[str]:
        """
        下载语音文件

        Args:
            media_id: 媒体文件 ID

        Returns:
            本地文件路径
        """
        try:
            # 先获取媒体 URL
            result = self._make_request(
                "GET",
                f"{media_id}",
                headers={"Authorization": f"Bearer {self.token}"}
            )

            if not result:
                return None

            media_url = result.get("url")
            if not media_url:
                return None

            # 下载文件
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(media_url, headers=headers, timeout=60)
            response.raise_for_status()

            # 保存文件
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # WhatsApp 语音通常是 ogg 格式
            file_path = temp_dir / f"whatsapp_voice_{media_id}.ogg"
            with open(file_path, "wb") as f:
                f.write(response.content)

            logger.info(f"语音下载完成: {file_path}")
            return str(file_path)

        except requests.RequestException as e:
            logger.error(f"下载语音失败: {e}")
            return None
        except Exception as e:
            logger.error(f"保存语音文件失败: {e}")
            return None

    def send_voice(self, chat_id: str, file_path: str) -> bool:
        """
        发送语音消息

        Args:
            chat_id: 用户手机号 (带国家代码)
            file_path: 语音文件路径

        Returns:
            是否发送成功
        """
        try:
            # WhatsApp 需要先上传媒体
            media_id = self._upload_media(file_path, "audio")
            if not media_id:
                return False

            # 发送音频消息
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": chat_id,
                "type": "audio",
                "audio": {"id": media_id}
            }

            result = self._make_request(
                "POST",
                f"{self.phone_number_id}/messages",
                json=data
            )

            if result:
                logger.info(f"语音发送成功: {chat_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"发送语音失败: {e}")
            return False

    def _upload_media(self, file_path: str, media_type: str = "audio") -> Optional[str]:
        """上传媒体文件"""
        try:
            url = f"{self.API_BASE}/{self.phone_number_id}/media"
            headers = {"Authorization": f"Bearer {self.token}"}

            with open(file_path, "rb") as f:
                files = {"file": (Path(file_path).name, f)}
                data = {"messaging_product": "whatsapp", "type": media_type}
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)

            response.raise_for_status()
            result = response.json()

            return result.get("id")

        except Exception as e:
            logger.error(f"上传媒体失败: {e}")
            return None

    def send_text(self, chat_id: str, text: str) -> bool:
        """
        发送文本消息

        Args:
            chat_id: 用户手机号
            text: 文本内容

        Returns:
            是否发送成功
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": chat_id,
            "type": "text",
            "text": {"body": text}
        }

        result = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            json=data
        )

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
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return None

            message = messages[0]
            msg_id = message.get("id")
            from_user = message.get("from")
            msg_type = message.get("type")
            timestamp = int(message.get("timestamp", 0))

            user = User(id=from_user)

            text = None
            voice_file = None

            if msg_type == "text":
                text = message.get("text", {}).get("body")
            elif msg_type == "audio":
                voice_file = message.get("audio", {}).get("id")

            return Message(
                id=msg_id,
                user=user,
                text=text,
                voice_file=voice_file,
                chat_id=from_user,
                timestamp=timestamp,
                extra={"raw": data}
            )

        except Exception as e:
            logger.error(f"解析 Webhook 失败: {e}")
            return None

    def verify_webhook(self, signature: str, body: bytes) -> bool:
        """
        验证 WhatsApp Webhook 签名

        Args:
            signature: 签名
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

            expected = hmac.new(
                secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(f"sha256={expected}", signature)

        except Exception as e:
            logger.error(f"验证签名失败: {e}")
            return False

    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取消息（WhatsApp 使用 Webhook 回调，这里返回空列表）

        Args:
            limit: 最大数量

        Returns:
            消息列表
        """
        # WhatsApp 使用 Webhook 回调，不支持主动拉取
        return []

    def parse_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """
        解析消息数据

        Args:
            data: 消息数据

        Returns:
            Message 对象
        """
        return self.parse_webhook(data)
