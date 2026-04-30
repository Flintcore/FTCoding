"""Tests for configuration system."""
import pytest
from pathlib import Path
from ftcoding.kernel.config import Config, load_config


class TestConfig:
    def test_default_values(self):
        config = Config()
        assert config.project_root == Path.cwd()
        assert config.llm_provider == "ollama"
        assert config.llm_model == "codellama"
        assert config.vector_db_path == ".ftcoding/vectors"
        assert config.memory_db_path == ".ftcoding/memory.db"

    def test_load_from_dict(self):
        data = {
            "project_root": "/tmp/test",
            "llm_provider": "openai",
            "llm_model": "gpt-4",
        }
        config = Config(**data)
        assert config.project_root == Path("/tmp/test")
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"

    def test_load_config_creates_default(self, temp_dir):
        config_path = temp_dir / "nonexistent.yaml"
        config = load_config(config_path)
        assert config.llm_provider == "ollama"

    def test_config_to_dict(self):
        config = Config(llm_provider="test")
        d = config.to_dict()
        assert d["llm_provider"] == "test"
        assert d["llm_model"] == "codellama"
