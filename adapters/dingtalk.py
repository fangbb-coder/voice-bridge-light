"""
钉钉适配器
"""

import time
import hmac
import hashlib
import base64
import requests
from typing import Optional, Dict, Any
from pathlib import Path
from urllib.parse import quote

from adapters.base import BaseAdapter, Message, User
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DingTalkAdapter(BaseAdapter):
    """钉钉适配器"""

    API_BASE = "https://oapi.dingtalk.com"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0

    def _get_access_token(self) -> Optional[str]:
        """获取 Access Token"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        try:
            url = f"{self.API_BASE}/gettoken"
            params = {
                "appkey": self.app_id,
                "appsecret": self.app_secret
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("errcode") != 0:
                logger.error(f"获取 Access Token 失败: {data}")
                return None

            self.access_token = data.get("access_token")
            self.token_expires_at = time.time() + data.get("expires_in", 7200) - 300

            return self.access_token

        except requests.RequestException as e:
            logger.error(f"请求 Access Token 失败: {e}")
            return None

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """调用钉钉 API"""
        token = self._get_access_token()
        if not token:
            return None

        url = f"{self.API_BASE}{endpoint}"

        try:
            if method.upper() == "GET":
                kwargs.setdefault("params", {})["access_token"] = token
                response = requests.get(url, **kwargs, timeout=30)
            else:
                kwargs.setdefault("params", {})["access_token"] = token
                response = requests.post(url, **kwargs, timeout=30)

            response.raise_for_status()
            data = response.json()

            if data.get("errcode") != 0:
                logger.error(f"钉钉 API 错误: {data}")
                return None

            return data

        except requests.RequestException as e:
            logger.error(f"钉钉请求失败: {e}")
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
            token = self._get_access_token()
            if not token:
                return None

            url = f"{self.API_BASE}/media/downloadFile"
            params = {"access_token": token, "media_id": media_id}

            response = requests.get(url, params=params, timeout=60, stream=True)
            response.raise_for_status()

            # 保存文件
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 钉钉语音通常是 amr 格式
            file_path = temp_dir / f"dingtalk_voice_{media_id}.amr"
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

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
            chat_id: 聊天 ID (用户 ID)
            file_path: 语音文件路径

        Returns:
            是否发送成功
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"语音文件不存在: {file_path}")
                return False

            # 钉钉不支持直接发送语音文件，需要转换为文件消息
            # 或者使用语音转文字后发送文本
            logger.warning("钉钉适配器暂不支持直接发送语音，将发送文本提示")
            return self.send_text(chat_id, "[语音消息]")

        except Exception as e:
            logger.error(f"发送语音失败: {e}")
            return False

    def send_text(self, chat_id: str, text: str) -> bool:
        """
        发送文本消息

        Args:
            chat_id: 用户 ID
            text: 文本内容

        Returns:
            是否发送成功
        """
        data = {
            "userid": chat_id,
            "msg": {
                "msgtype": "text",
                "text": {"content": text}
            }
        }

        result = self._make_request("POST", "/topapi/message/corpconversation/asyncsend_v2", json=data)
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
            # 钉钉机器人消息
            msg_type = data.get("msgtype")
            chat_id = data.get("senderStaffId")

            user = User(
                id=chat_id,
                name=data.get("senderNick")
            )

            text = None
            voice_file = None

            if msg_type == "text":
                text = data.get("text", {}).get("content")
            elif msg_type == "voice":
                # 钉钉语音消息
                voice_file = data.get("mediaId")
                content = data.get("content")
                if content:
                    text = content

            return Message(
                id=data.get("msgId", ""),
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

    def verify_webhook(self, timestamp: str, sign: str) -> bool:
        """
        验证钉钉 Webhook 签名

        Args:
            timestamp: 时间戳
            sign: 签名

        Returns:
            是否验证通过
        """
        try:
            secret = self.webhook_secret
            if not secret:
                return True

            # 钉钉签名算法
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()
            my_sign = quote(base64.b64encode(hmac_code).decode("utf-8"))

            return my_sign == sign

        except Exception as e:
            logger.error(f"验证签名失败: {e}")
            return False

    def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户信息"""
        return self._make_request("POST", "/topapi/v2/user/get", json={"userid": user_id})
