"""
Telegram 适配器
"""

import os
import requests
from typing import Optional, Dict, Any
from pathlib import Path

from adapters.base import BaseAdapter, Message, User
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TelegramAdapter(BaseAdapter):
    """Telegram Bot 适配器"""

    API_BASE = "https://api.telegram.org/bot{token}"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base = self.API_BASE.format(token=self.token)

    def _make_request(self, method: str, **params) -> Optional[dict]:
        """
        调用 Telegram API

        Args:
            method: API 方法名
            **params: 请求参数

        Returns:
            API 响应
        """
        url = f"{self.api_base}/{method}"

        try:
            response = requests.post(url, json=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                logger.error(f"Telegram API 错误: {data.get('description')}")
                return None

            return data.get("result")

        except requests.RequestException as e:
            logger.error(f"Telegram 请求失败: {e}")
            return None

    def _make_file_request(self, method: str, files: dict, data: dict = None) -> Optional[dict]:
        """
        调用文件上传 API

        Args:
            method: API 方法名
            files: 文件字典
            data: 其他数据

        Returns:
            API 响应
        """
        url = f"{self.api_base}/{method}"

        try:
            response = requests.post(url, files=files, data=data, timeout=60)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API 错误: {result.get('description')}")
                return None

            return result.get("result")

        except requests.RequestException as e:
            logger.error(f"Telegram 文件请求失败: {e}")
            return None

    def get_file_url(self, file_id: str) -> Optional[str]:
        """
        获取文件下载链接

        Args:
            file_id: 文件 ID

        Returns:
            文件下载 URL
        """
        result = self._make_request("getFile", file_id=file_id)
        if not result:
            return None

        file_path = result.get("file_path")
        if not file_path:
            return None

        # 构建下载 URL
        return f"https://api.telegram.org/file/bot{self.token}/{file_path}"

    def download_voice(self, file_id: str) -> Optional[str]:
        """
        下载语音文件

        Args:
            file_id: 文件 ID

        Returns:
            本地文件路径
        """
        try:
            # 获取文件 URL
            file_url = self.get_file_url(file_id)
            if not file_url:
                logger.error(f"无法获取文件 URL: {file_id}")
                return None

            # 下载文件
            response = requests.get(file_url, timeout=60)
            response.raise_for_status()

            # 保存到临时目录
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Telegram 语音通常是 .oga 格式
            file_path = temp_dir / f"tg_voice_{file_id}.oga"
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
            chat_id: 聊天 ID
            file_path: 语音文件路径

        Returns:
            是否发送成功
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"语音文件不存在: {file_path}")
                return False

            with open(path, "rb") as f:
                files = {"voice": f}
                data = {"chat_id": chat_id}
                result = self._make_file_request("sendVoice", files=files, data=data)

            if result:
                logger.info(f"语音发送成功: {chat_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"发送语音失败: {e}")
            return False

    def send_text(self, chat_id: str, text: str) -> bool:
        """
        发送文本消息

        Args:
            chat_id: 聊天 ID
            text: 文本内容

        Returns:
            是否发送成功
        """
        result = self._make_request("sendMessage", chat_id=chat_id, text=text)
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
            # 获取消息数据
            message = data.get("message") or data.get("edited_message")
            if not message:
                return None

            msg_id = str(message.get("message_id", ""))
            chat = message.get("chat", {})
            chat_id = str(chat.get("id", ""))

            # 获取用户信息
            from_user = message.get("from", {})
            user = User(
                id=str(from_user.get("id", "")),
                name=from_user.get("first_name", ""),
                extra={
                    "username": from_user.get("username"),
                    "language_code": from_user.get("language_code")
                }
            )

            # 获取文本
            text = message.get("text")

            # 获取语音
            voice_url = None
            voice_file_id = None
            voice = message.get("voice") or message.get("audio")
            if voice:
                voice_file_id = voice.get("file_id")

            return Message(
                id=msg_id,
                user=user,
                text=text,
                voice_url=voice_url,
                voice_file=voice_file_id,
                chat_id=chat_id,
                timestamp=message.get("date"),
                extra={"raw": data}
            )

        except Exception as e:
            logger.error(f"解析 Webhook 失败: {e}")
            return None

    def set_webhook(self, url: str) -> bool:
        """
        设置 Webhook

        Args:
            url: Webhook URL

        Returns:
            是否设置成功
        """
        result = self._make_request("setWebhook", url=url)
        if result:
            logger.info(f"Webhook 设置成功: {url}")
            return True
        return False

    def delete_webhook(self) -> bool:
        """删除 Webhook"""
        result = self._make_request("deleteWebhook")
        if result:
            logger.info("Webhook 已删除")
            return True
        return False

    def get_me(self) -> Optional[dict]:
        """获取 Bot 信息"""
        return self._make_request("getMe")
