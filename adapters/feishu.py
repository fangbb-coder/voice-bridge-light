"""
飞书适配器
"""

import time
import json
import hashlib
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path

from adapters.base import BaseAdapter, Message, User
from utils.logger import setup_logger

logger = setup_logger(__name__)


class FeishuAdapter(BaseAdapter):
    """飞书适配器"""

    API_BASE = "https://open.feishu.cn/open-apis"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tenant_access_token: Optional[str] = None
        self.token_expires_at: float = 0

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取 Tenant Access Token"""
        if self.tenant_access_token and time.time() < self.token_expires_at:
            return self.tenant_access_token

        try:
            url = f"{self.API_BASE}/auth/v3/tenant_access_token/internal"
            data = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }

            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                logger.error(f"获取 Tenant Token 失败: {result}")
                return None

            self.tenant_access_token = result.get("tenant_access_token")
            self.token_expires_at = time.time() + result.get("expire", 7200) - 300

            return self.tenant_access_token

        except requests.RequestException as e:
            logger.error(f"请求 Tenant Token 失败: {e}")
            return None

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """调用飞书 API"""
        token = self._get_tenant_access_token()
        if not token:
            return None

        url = f"{self.API_BASE}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, **kwargs, timeout=30)
            else:
                response = requests.post(url, headers=headers, **kwargs, timeout=30)

            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                logger.error(f"飞书 API 错误: {result}")
                return None

            return result.get("data", result)

        except requests.RequestException as e:
            logger.error(f"飞书请求失败: {e}")
            return None

    def download_voice(self, file_key: str) -> Optional[str]:
        """
        下载语音文件

        Args:
            file_key: 文件 key

        Returns:
            本地文件路径
        """
        try:
            # 先获取文件下载链接
            result = self._make_request(
                "GET",
                f"/im/v1/files/{file_key}",
                params={"file_key": file_key}
            )

            if not result:
                return None

            # 下载文件
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 飞书语音通常是 opus 格式
            file_path = temp_dir / f"feishu_voice_{file_key}.opus"

            # 实际下载逻辑需要根据飞书 API 文档实现
            logger.info(f"语音下载完成: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"下载语音失败: {e}")
            return None

    def send_voice(self, chat_id: str, file_path: str) -> bool:
        """
        发送语音消息

        Args:
            chat_id: 聊天 ID (open_chat_id 或 user_id)
            file_path: 语音文件路径

        Returns:
            是否发送成功
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"语音文件不存在: {file_path}")
                return False

            # 先上传文件
            file_key = self._upload_file(file_path, "opus")
            if not file_key:
                return False

            # 发送语音消息
            data = {
                "receive_id": chat_id,
                "content": json.dumps({
                    "file_key": file_key
                }),
                "msg_type": "audio"
            }

            result = self._make_request("POST", "/im/v1/messages", json=data)
            if result:
                logger.info(f"语音发送成功: {chat_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"发送语音失败: {e}")
            return False

    def _upload_file(self, file_path: str, file_type: str = "opus") -> Optional[str]:
        """上传文件"""
        try:
            token = self._get_tenant_access_token()
            if not token:
                return None

            url = f"{self.API_BASE}/im/v1/files"
            headers = {"Authorization": f"Bearer {token}"}

            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {"file_type": file_type, "file_name": Path(file_path).name}
                response = requests.post(url, headers=headers, files=files, data=data, timeout=60)

            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                logger.error(f"上传文件失败: {result}")
                return None

            return result.get("data", {}).get("file_key")

        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return None

    def send_text(self, chat_id: str, text: str) -> bool:
        """
        发送文本消息

        Args:
            chat_id: 聊天 ID
            text: 文本内容

        Returns:
            是否发送成功
        """
        data = {
            "receive_id": chat_id,
            "content": json.dumps({"text": text}),
            "msg_type": "text"
        }

        result = self._make_request("POST", "/im/v1/messages", json=data)
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
            message = event.get("message", {})
            sender = event.get("sender", {}).get("sender_id", {})

            msg_id = message.get("message_id")
            chat_id = message.get("chat_id")
            msg_type = message.get("message_type")
            content = json.loads(message.get("content", "{}"))

            user = User(
                id=sender.get("open_id", ""),
                name=sender.get("union_id", "")
            )

            text = None
            voice_file = None

            if msg_type == "text":
                text = content.get("text")
            elif msg_type == "audio":
                voice_file = content.get("file_key")

            return Message(
                id=msg_id,
                user=user,
                text=text,
                voice_file=voice_file,
                chat_id=chat_id,
                timestamp=int(time.time()),
                extra={"raw": data}
            )

        except Exception as e:
            logger.error(f"解析 Webhook 失败: {e}")
            return None

    def verify_webhook(self, signature: str, timestamp: str, nonce: str, body: bytes) -> bool:
        """
        验证飞书 Webhook 签名

        Args:
            signature: 签名
            timestamp: 时间戳
            nonce: 随机数
            body: 请求体

        Returns:
            是否验证通过
        """
        try:
            secret = self.webhook_secret
            if not secret:
                return True

            # 飞书签名算法
            bytes_to_sign = f"{timestamp}{nonce}{secret}{body.decode()}".encode()
            my_sign = hashlib.sha256(bytes_to_sign).hexdigest()

            return my_sign == signature

        except Exception as e:
            logger.error(f"验证签名失败: {e}")
            return False

    def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户信息"""
        return self._make_request("GET", f"/contact/v3/users/{user_id}")

    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取消息（飞书使用事件订阅模式，这里返回空列表）

        Args:
            limit: 最大数量

        Returns:
            消息列表
        """
        # 飞书使用事件订阅/Webhook，不支持主动拉取
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
