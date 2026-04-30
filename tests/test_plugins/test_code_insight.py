"""Tests for code insight plugin."""
import pytest
from ftcoding.plugins.code_insight.plugin import CodeInsightPlugin
from ftcoding.plugins.base import PluginContext
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


class TestCodeInsightPlugin:
    @pytest.fixture
    async def plugin(self, temp_dir):
        bus = MessageBus()
        config = Config(project_root=temp_dir, vector_db_path=str(temp_dir / "vectors"))
        ctx = PluginContext(bus=bus, config=config, data_dir=str(temp_dir / "data"))

        p = CodeInsightPlugin()
        await p.initialize(ctx)
        yield p
        await p.shutdown()

    @pytest.mark.asyncio
    async def test_index_project(self, plugin, sample_python_project):
        result = await plugin.handle("index_project", {"path": str(sample_python_project)})
        assert result["success"] is True
        assert result["files_indexed"] > 0

    @pytest.mark.asyncio
    async def test_search_code(self, plugin, sample_python_project):
        await plugin.handle("index_project", {"path": str(sample_python_project)})
        result = await plugin.handle("search_code", {"query": "calculator multiply"})
        assert result["success"] is True
        assert len(result["results"]) > 0

    @pytest.mark.asyncio
    async def test_get_file_structure(self, plugin, sample_python_project):
        result = await plugin.handle("get_structure", {"path": str(sample_python_project)})
        assert result["success"] is True
        assert "src" in str(result["structure"])
