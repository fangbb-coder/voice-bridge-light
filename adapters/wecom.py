"""
企业微信适配器
"""

import os
import time
import json
import hashlib
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path

from adapters.base import BaseAdapter, Message, User
from utils.logger import setup_logger

logger = setup_logger(__name__)


class WeComAdapter(BaseAdapter):
    """企业微信适配器"""

    API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0

    def _get_access_token(self) -> Optional[str]:
        """获取 Access Token"""
        # 检查缓存
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        try:
            url = f"{self.API_BASE}/gettoken"
            params = {
                "corpid": self.app_id,
                "corpsecret": self.app_secret
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("errcode") != 0:
                logger.error(f"获取 Access Token 失败: {data}")
                return None

            self.access_token = data.get("access_token")
            # 提前 5 分钟过期
            self.token_expires_at = time.time() + data.get("expires_in", 7200) - 300

            return self.access_token

        except requests.RequestException as e:
            logger.error(f"请求 Access Token 失败: {e}")
            return None

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """
        调用企业微信 API

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 请求参数

        Returns:
            API 响应
        """
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
                logger.error(f"企业微信 API 错误: {data}")
                return None

            return data

        except requests.RequestException as e:
            logger.error(f"企业微信请求失败: {e}")
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

            url = f"{self.API_BASE}/media/get"
            params = {"access_token": token, "media_id": media_id}

            response = requests.get(url, params=params, timeout=60, stream=True)
            response.raise_for_status()

            # 检查是否为 JSON 错误
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = response.json()
                logger.error(f"下载媒体失败: {data}")
                return None

            # 保存文件
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 企业微信语音通常是 amr 格式
            file_path = temp_dir / f"wecom_voice_{media_id}.amr"
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

            # 先上传临时素材
            media_id = self._upload_media(file_path, "voice")
            if not media_id:
                return False

            # 发送消息
            data = {
                "touser": chat_id,
                "msgtype": "voice",
                "voice": {"media_id": media_id}
            }

            result = self._make_request("POST", "/message/send", json=data)
            if result:
                logger.info(f"语音发送成功: {chat_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"发送语音失败: {e}")
            return False

    def _upload_media(self, file_path: str, media_type: str = "voice") -> Optional[str]:
        """
        上传临时素材

        Args:
            file_path: 文件路径
            media_type: 媒体类型

        Returns:
            media_id
        """
        try:
            token = self._get_access_token()
            if not token:
                return None

            url = f"{self.API_BASE}/media/upload"
            params = {"access_token": token, "type": media_type}

            with open(file_path, "rb") as f:
                files = {"media": f}
                response = requests.post(url, params=params, files=files, timeout=60)

            response.raise_for_status()
            data = response.json()

            if data.get("errcode") != 0:
                logger.error(f"上传媒体失败: {data}")
                return None

            return data.get("media_id")

        except Exception as e:
            logger.error(f"上传媒体失败: {e}")
            return None

    def send_text(self, chat_id: str, text: str) -> bool:
        """
        发送文本消息

        Args:
            chat_id: 聊天 ID (用户 ID)
            text: 文本内容

        Returns:
            是否发送成功
        """
        data = {
            "touser": chat_id,
            "msgtype": "text",
            "text": {"content": text}
        }

        result = self._make_request("POST", "/message/send", json=data)
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
            msg_type = data.get("MsgType")
            user_id = data.get("FromUserName")
            chat_id = data.get("ToUserName")
            msg_id = data.get("MsgId") or data.get("MsgID")
            timestamp = int(data.get("CreateTime", 0))

            user = User(id=user_id)

            text = None
            voice_file = None

            if msg_type == "text":
                text = data.get("Content")
            elif msg_type == "voice":
                voice_file = data.get("MediaId")
                # 企业微信语音消息可能包含识别文本
                recognition = data.get("Recognition")
                if recognition:
                    text = recognition

            return Message(
                id=str(msg_id) if msg_id else "",
                user=user,
                text=text,
                voice_file=voice_file,
                chat_id=chat_id,
                timestamp=timestamp,
                extra={"raw": data, "msg_type": msg_type}
            )

        except Exception as e:
            logger.error(f"解析 Webhook 失败: {e}")
            return None

    def verify_webhook(self, signature: str, timestamp: str, nonce: str, echo_str: str = "") -> bool:
        """
        验证企业微信 Webhook 签名

        Args:
            signature: 签名
            timestamp: 时间戳
            nonce: 随机数
            echo_str: 回显字符串

        Returns:
            是否验证通过
        """
        try:
            token = self.webhook_secret
            if not token:
                return True

            # 拼接字符串并排序
            tmp_list = [token, timestamp, nonce, echo_str]
            tmp_list.sort()
            tmp_str = "".join(tmp_list)

            # SHA1 签名
            hashcode = hashlib.sha1(tmp_str.encode()).hexdigest()

            return hashcode == signature

        except Exception as e:
            logger.error(f"验证签名失败: {e}")
            return False

    def get_user_info(self, user_id: str) -> Optional[dict]:
        """
        获取用户信息

        Args:
            user_id: 用户 ID

        Returns:
            用户信息
        """
        return self._make_request("GET", "/user/get", params={"userid": user_id})

    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取消息（企业微信使用回调模式，这里返回空列表）

        Args:
            limit: 最大数量

        Returns:
            消息列表
        """
        # 企业微信使用 Webhook 回调，不支持主动拉取
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
