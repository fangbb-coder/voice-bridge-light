"""
适配器包 - 支持多种 IM 平台
"""

from typing import Dict, Type
from adapters.base import BaseAdapter, Message, User

# 适配器注册表
_ADAPTER_REGISTRY: Dict[str, Type[BaseAdapter]] = {}


def register_adapter(name: str, adapter_class: Type[BaseAdapter]) -> None:
    """注册适配器"""
    _ADAPTER_REGISTRY[name] = adapter_class


def get_adapter(name: str, config: dict) -> BaseAdapter:
    """
    获取适配器实例

    Args:
        name: 适配器名称
        config: 配置字典

    Returns:
        适配器实例
    """
    if name not in _ADAPTER_REGISTRY:
        raise ValueError(f"未注册的适配器: {name}")

    return _ADAPTER_REGISTRY[name](config)


def list_adapters() -> list:
    """列出所有已注册的适配器"""
    return list(_ADAPTER_REGISTRY.keys())


# 延迟导入并注册适配器
def _register_all():
    try:
        from adapters.telegram import TelegramAdapter
        register_adapter("telegram", TelegramAdapter)
    except ImportError as e:
        pass

    try:
        from adapters.wecom import WeComAdapter
        register_adapter("wecom", WeComAdapter)
    except ImportError:
        pass

    try:
        from adapters.dingtalk import DingTalkAdapter
        register_adapter("dingtalk", DingTalkAdapter)
    except ImportError:
        pass

    try:
        from adapters.feishu import FeishuAdapter
        register_adapter("feishu", FeishuAdapter)
    except ImportError:
        pass

    try:
        from adapters.whatsapp import WhatsAppAdapter
        register_adapter("whatsapp", WhatsAppAdapter)
    except ImportError:
        pass

    try:
        from adapters.qq import QQAdapter
        register_adapter("qq", QQAdapter)
    except ImportError:
        pass


_register_all()

__all__ = [
    "BaseAdapter",
    "Message",
    "User",
    "get_adapter",
    "register_adapter",
    "list_adapters",
]
