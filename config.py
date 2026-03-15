"""
配置管理模块
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class TTSConfig:
    """TTS 配置"""
    speed: float = 1.0
    pitch: float = 1.0
    voice: str = "af"  # 默认女声

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TTSConfig":
        return cls(
            speed=data.get("speed", 1.0),
            pitch=data.get("pitch", 1.0),
            voice=data.get("voice", "af")
        )


@dataclass
class AdapterConfig:
    """适配器配置"""
    enabled: bool = False
    token: Optional[str] = None
    webhook_secret: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdapterConfig":
        return cls(
            enabled=data.get("enabled", False),
            token=data.get("token"),
            webhook_secret=data.get("webhook_secret"),
            app_id=data.get("app_id"),
            app_secret=data.get("app_secret"),
            extra=data.get("extra", {})
        )


@dataclass
class Config:
    """主配置类"""
    language: str = "zh"
    voice: str = "female"
    wake_word: str = "hey claw"
    auto_voice_reply: bool = True

    # 模型路径
    asr_model_dir: str = "models/whisper"
    tts_model_dir: str = "models/piper"

    # 临时文件
    temp_dir: str = "temp"
    max_temp_files: int = 100

    # TTS 配置
    tts: TTSConfig = field(default_factory=TTSConfig)

    # 适配器配置
    adapters: Dict[str, AdapterConfig] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """
        从 YAML 文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            Config 实例
        """
        config = cls()

        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return config

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

            # 基础配置
            config.language = data.get("language", config.language)
            config.voice = data.get("voice", config.voice)
            config.wake_word = data.get("wake_word", config.wake_word)
            config.auto_voice_reply = data.get("auto_voice_reply", config.auto_voice_reply)

            # 模型路径
            config.asr_model_dir = data.get("asr_model_dir", config.asr_model_dir)
            config.tts_model_dir = data.get("tts_model_dir", config.tts_model_dir)

            # 临时文件
            config.temp_dir = data.get("temp_dir", config.temp_dir)
            config.max_temp_files = data.get("max_temp_files", config.max_temp_files)

            # TTS 配置
            if "tts" in data:
                config.tts = TTSConfig.from_dict(data["tts"])

            # 适配器配置
            if "adapters" in data:
                for name, adapter_data in data["adapters"].items():
                    config.adapters[name] = AdapterConfig.from_dict(adapter_data)

            logger.info(f"配置加载成功: {config_path}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            return config
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return config

    def save(self, config_path: str = "config.yaml") -> bool:
        """
        保存配置到 YAML 文件

        Args:
            config_path: 配置文件路径

        Returns:
            是否保存成功
        """
        try:
            data = {
                "language": self.language,
                "voice": self.voice,
                "wake_word": self.wake_word,
                "auto_voice_reply": self.auto_voice_reply,
                "asr_model_dir": self.asr_model_dir,
                "tts_model_dir": self.tts_model_dir,
                "temp_dir": self.temp_dir,
                "max_temp_files": self.max_temp_files,
                "tts": {
                    "speed": self.tts.speed,
                    "pitch": self.tts.pitch,
                    "voice": self.tts.voice
                },
                "adapters": {}
            }

            for name, adapter in self.adapters.items():
                data["adapters"][name] = {
                    "enabled": adapter.enabled,
                    "token": adapter.token,
                    "webhook_secret": adapter.webhook_secret,
                    "app_id": adapter.app_id,
                    "app_secret": adapter.app_secret,
                    "extra": adapter.extra
                }

            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"配置保存成功: {config_path}")
            return True

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def get_adapter(self, name: str) -> Optional[AdapterConfig]:
        """获取适配器配置"""
        return self.adapters.get(name)

    def ensure_dirs(self) -> None:
        """确保必要的目录存在"""
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        Path(self.asr_model_dir).mkdir(parents=True, exist_ok=True)
        Path(self.tts_model_dir).mkdir(parents=True, exist_ok=True)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.load()
        _config.ensure_dirs()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config.load()
    _config.ensure_dirs()
    return _config
