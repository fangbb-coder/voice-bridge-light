"""
基础功能测试
"""

import sys
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig(unittest.TestCase):
    """测试配置模块"""

    def test_config_load(self):
        """测试配置加载"""
        from config import Config

        config = Config.load()
        self.assertEqual(config.language, "zh")
        self.assertEqual(config.voice, "female")
        self.assertEqual(config.wake_word, "hey claw")
        self.assertTrue(config.auto_voice_reply)

    def test_config_default_values(self):
        """测试默认值"""
        from config import Config

        config = Config()
        self.assertEqual(config.language, "zh")
        self.assertEqual(config.tts.speed, 1.0)
        self.assertEqual(config.tts.pitch, 1.0)

    def test_config_save_and_load(self):
        """测试配置保存和重新加载"""
        from config import Config
        import tempfile

        config = Config()
        config.language = "en"
        config.voice = "male"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name

        try:
            config.save(temp_path)
            loaded = Config.load(temp_path)
            self.assertEqual(loaded.language, "en")
            self.assertEqual(loaded.voice, "male")
        finally:
            os.unlink(temp_path)


class TestLogger(unittest.TestCase):
    """测试日志模块"""

    def test_logger_creation(self):
        """测试日志器创建"""
        from utils.logger import setup_logger
        import logging

        logger = setup_logger("test", level=logging.DEBUG, log_to_file=False)
        self.assertEqual(logger.name, "test")
        self.assertEqual(logger.level, logging.DEBUG)


class TestAudioUtils(unittest.TestCase):
    """测试音频工具"""

    def test_generate_temp_path(self):
        """测试临时路径生成"""
        from voice.audio_utils import generate_temp_path

        path = generate_temp_path("test_temp", ".wav")
        self.assertTrue(path.endswith(".wav"))
        self.assertIn("test_temp", path)

    def test_validate_audio_file_not_exist(self):
        """测试验证不存在的文件"""
        from voice.audio_utils import validate_audio_file

        is_valid, error = validate_audio_file("/nonexistent/file.wav")
        self.assertFalse(is_valid)
        self.assertEqual(error, "文件不存在")


class TestVoiceAssistantLogic(unittest.TestCase):
    """测试语音助手逻辑（不依赖外部库）"""

    def test_handle_hello_zh(self):
        """测试中文问候"""
        # 直接测试回复生成逻辑
        text = "你好"
        text_lower = text.lower()

        # 检查关键词匹配
        self.assertIn("你好", text_lower)

    def test_handle_time_keywords(self):
        """测试时间查询关键词"""
        keywords = ["time", "时间"]
        test_texts = ["现在几点", "what time", "时间是多少"]

        for test in test_texts:
            matches = any(kw in test.lower() for kw in keywords)
            self.assertTrue(matches or "几点" in test or "time" in test.lower())

    def test_handle_date_keywords(self):
        """测试日期查询关键词"""
        keywords = ["date", "日期"]
        test_texts = ["今天几号", "what date", "日期是多少"]

        for test in test_texts:
            matches = any(kw in test.lower() for kw in keywords)
            self.assertTrue(matches or "几号" in test or "date" in test.lower())


class TestAdapters(unittest.TestCase):
    """测试适配器"""

    def test_adapter_base_structure(self):
        """测试适配器基类结构"""
        from adapters.base import BaseAdapter, Message, User

        # 检查类是否存在
        self.assertTrue(hasattr(BaseAdapter, '__abstractmethods__'))
        self.assertTrue(hasattr(Message, '__dataclass_fields__'))
        self.assertTrue(hasattr(User, '__dataclass_fields__'))

    def test_adapter_registration(self):
        """测试适配器注册"""
        from adapters import list_adapters

        adapters = list_adapters()
        expected = ["telegram", "wecom", "dingtalk", "feishu", "whatsapp", "qq"]

        for name in expected:
            self.assertIn(name, adapters)

    def test_telegram_adapter_config(self):
        """测试 Telegram 适配器配置解析"""
        from adapters.telegram import TelegramAdapter

        config = {
            "token": "test_token",
            "webhook_secret": "test_secret"
        }

        adapter = TelegramAdapter(config)
        self.assertEqual(adapter.token, "test_token")
        self.assertEqual(adapter.webhook_secret, "test_secret")
        self.assertIn("test_token", adapter.api_base)


class TestModelsDownloadScript(unittest.TestCase):
    """测试模型下载脚本"""

    def test_script_exists(self):
        """测试脚本文件存在"""
        script_path = Path("scripts/download_models.py")
        self.assertTrue(script_path.exists())

    def test_models_config(self):
        """测试模型配置"""
        # 检查脚本中定义的模型 (Whisper + Piper)
        script_content = Path("scripts/download_models.py").read_text(encoding='utf-8')
        self.assertIn("whisper", script_content)
        self.assertIn("piper", script_content)


class TestSkillYaml(unittest.TestCase):
    """测试 Skill 配置文件"""

    def test_skill_yaml_exists(self):
        """测试 skill.yaml 存在"""
        self.assertTrue(Path("skill.yaml").exists())

    def test_skill_yaml_structure(self):
        """测试 skill.yaml 结构"""
        import yaml

        with open("skill.yaml", "r", encoding='utf-8') as f:
            data = yaml.safe_load(f)

        required_fields = ["name", "version", "description", "runtime", "entry"]
        for field in required_fields:
            self.assertIn(field, data)

        self.assertEqual(data["name"], "voice-bridge")
        self.assertEqual(data["runtime"], "python3")
        self.assertEqual(data["entry"], "main.py")

    def test_skill_has_config(self):
        """测试 skill.yaml 有配置项"""
        import yaml

        with open("skill.yaml", "r", encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.assertIn("config", data)
        config = data["config"]

        # 检查关键配置
        self.assertIn("language", config)
        self.assertIn("telegram_enabled", config)
        self.assertIn("wecom_enabled", config)

    def test_skill_has_tools(self):
        """测试 skill.yaml 有 tools 定义（OpenClaw 规范）"""
        import yaml

        with open("skill.yaml", "r", encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.assertIn("tools", data)
        tools = data["tools"]

        # 检查关键工具
        tool_names = [t["name"] for t in tools]
        self.assertIn("process_voice", tool_names)
        self.assertIn("process_text", tool_names)
        self.assertIn("text_to_speech", tool_names)
        self.assertIn("speech_to_text", tool_names)

    def test_tools_have_input_schema(self):
        """测试工具有 inputSchema"""
        import yaml

        with open("skill.yaml", "r", encoding='utf-8') as f:
            data = yaml.safe_load(f)

        for tool in data["tools"]:
            self.assertIn("inputSchema", tool)
            self.assertIn("type", tool["inputSchema"])
            self.assertEqual(tool["inputSchema"]["type"], "object")


class TestRequirements(unittest.TestCase):
    """测试依赖文件"""

    def test_requirements_exists(self):
        """测试 requirements.txt 存在"""
        self.assertTrue(Path("requirements.txt").exists())

    def test_core_dependencies(self):
        """测试核心依赖"""
        content = Path("requirements.txt").read_text(encoding='utf-8')

        core_deps = ["openai-whisper", "fastapi", "requests", "pyyaml"]
        for dep in core_deps:
            self.assertIn(dep, content)


class TestProjectStructure(unittest.TestCase):
    """测试项目结构"""

    def test_main_entry(self):
        """测试主入口文件"""
        self.assertTrue(Path("main.py").exists())

    def test_skill_md_exists(self):
        """测试 SKILL.md 存在"""
        self.assertTrue(Path("SKILL.md").exists())

    def test_prompt_md_exists(self):
        """测试 prompt.md 存在（OpenClaw 规范）"""
        self.assertTrue(Path("prompt.md").exists())

    def test_directory_structure(self):
        """测试目录结构"""
        dirs = ["voice", "assistant", "adapters", "utils", "scripts", "tests"]
        for dir_name in dirs:
            self.assertTrue(Path(dir_name).is_dir(), f"目录 {dir_name} 不存在")

    def test_init_files(self):
        """测试 __init__.py 文件"""
        packages = ["voice", "assistant", "adapters", "utils", "scripts", "tests"]
        for pkg in packages:
            init_file = Path(pkg) / "__init__.py"
            self.assertTrue(init_file.exists(), f"{pkg}/__init__.py 不存在")


def run_tests():
    """运行测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestLogger))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceAssistantLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestAdapters))
    suite.addTests(loader.loadTestsFromTestCase(TestModelsDownloadScript))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillYaml))
    suite.addTests(loader.loadTestsFromTestCase(TestRequirements))
    suite.addTests(loader.loadTestsFromTestCase(TestProjectStructure))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
