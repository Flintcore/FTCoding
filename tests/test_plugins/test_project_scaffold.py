"""Tests for project scaffold plugin."""
import pytest
from pathlib import Path
from ftcoding.plugins.project_scaffold.plugin import ProjectScaffoldPlugin
from ftcoding.plugins.base import PluginContext
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


class TestProjectScaffoldPlugin:
    @pytest.fixture
    async def plugin(self, temp_dir):
        bus = MessageBus()
        config = Config(project_root=temp_dir)
        ctx = PluginContext(bus=bus, config=config, data_dir=str(temp_dir / "data"))

        p = ProjectScaffoldPlugin()
        await p.initialize(ctx)
        yield p
        await p.shutdown()

    @pytest.mark.asyncio
    async def test_detect_type_python(self, plugin, temp_dir):
        (temp_dir / "pyproject.toml").write_text("[project]\n")
        result = await plugin.handle("detect_type", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result["type"] == "python"

    @pytest.mark.asyncio
    async def test_detect_type_javascript(self, plugin, temp_dir):
        (temp_dir / "package.json").write_text("{}\n")
        result = await plugin.handle("detect_type", {"path": str(temp_dir)})
        assert result["success"] is True
        assert "javascript" in result["detected"]

    @pytest.mark.asyncio
    async def test_detect_type_unknown(self, plugin, temp_dir):
        result = await plugin.handle("detect_type", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result["type"] == "unknown"

    @pytest.mark.asyncio
    async def test_init_python(self, plugin, temp_dir):
        result = await plugin.handle("init_python", {"path": str(temp_dir), "name": "test_proj"})
        assert result["success"] is True
        assert result["type"] == "python"
        assert "pyproject.toml" in result["created"]
        assert "README.md" in result["created"]
        assert ".gitignore" in result["created"]
        assert (temp_dir / "pyproject.toml").exists()
        assert (temp_dir / "test_proj" / "__init__.py").exists()

    @pytest.mark.asyncio
    async def test_init_javascript(self, plugin, temp_dir):
        result = await plugin.handle("init_javascript", {"path": str(temp_dir), "name": "js-app"})
        assert result["success"] is True
        assert result["type"] == "javascript"
        assert "package.json" in result["created"]
        assert (temp_dir / "package.json").exists()

    @pytest.mark.asyncio
    async def test_init_go(self, plugin, temp_dir):
        result = await plugin.handle("init_go", {"path": str(temp_dir), "name": "example.com/user/proj"})
        assert result["success"] is True
        assert result["type"] == "go"
        assert "go.mod" in result["created"]
        assert (temp_dir / "go.mod").exists()

    @pytest.mark.asyncio
    async def test_add_ci(self, plugin, temp_dir):
        result = await plugin.handle("add_ci", {"path": str(temp_dir)})
        assert result["success"] is True
        assert ".github/workflows/ci.yml" in result["created"]
        assert (temp_dir / ".github" / "workflows" / "ci.yml").exists()

    @pytest.mark.asyncio
    async def test_add_docker(self, plugin, temp_dir):
        result = await plugin.handle("add_docker", {"path": str(temp_dir)})
        assert result["success"] is True
        assert "Dockerfile" in result["created"]
        assert (temp_dir / "Dockerfile").exists()

    @pytest.mark.asyncio
    async def test_add_docker_compose(self, plugin, temp_dir):
        result = await plugin.handle("add_docker", {"path": str(temp_dir)})
        assert result["success"] is True
        assert "docker-compose.yml" in result["created"]
        assert (temp_dir / "docker-compose.yml").exists()

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing(self, plugin, temp_dir):
        (temp_dir / "README.md").write_text("existing\n")
        result = await plugin.handle("init_python", {"path": str(temp_dir), "name": "proj"})
        assert result["success"] is True
        # README.md should not be in created list since it already exists
        assert "README.md" not in result["created"]
        assert (temp_dir / "README.md").read_text() == "existing\n"
