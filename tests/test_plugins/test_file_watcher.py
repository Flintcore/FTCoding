"""Tests for file watcher plugin."""
import pytest
import time
from pathlib import Path
from ftcoding.plugins.file_watcher.plugin import FileWatcherPlugin
from ftcoding.plugins.base import PluginContext
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


class TestFileWatcherPlugin:
    @pytest.fixture
    async def plugin(self, temp_dir):
        bus = MessageBus()
        config = Config(project_root=temp_dir)
        ctx = PluginContext(bus=bus, config=config, data_dir=str(temp_dir / "data"))

        p = FileWatcherPlugin()
        await p.initialize(ctx)
        yield p
        await p.shutdown()

    @pytest.mark.asyncio
    async def test_watch(self, plugin):
        result = await plugin.handle("watch", {})
        assert result["success"] is True
        assert result["watching"] is True

    @pytest.mark.asyncio
    async def test_unwatch(self, plugin):
        await plugin.handle("watch", {})
        result = await plugin.handle("unwatch", {})
        assert result["success"] is True
        assert result["watching"] is False

    @pytest.mark.asyncio
    async def test_status(self, plugin, temp_dir):
        result = await plugin.handle("status", {})
        assert result["success"] is True
        assert result["watching"] is False
        assert result["project_root"] == str(temp_dir)

    @pytest.mark.asyncio
    async def test_scan_detects_new_file(self, plugin, temp_dir):
        await plugin.handle("watch", {})
        (temp_dir / "new.py").write_text("x = 1\n")

        result = await plugin.handle("scan", {})
        assert result["success"] is True
        assert result["changes_detected"] >= 1
        paths = [c["path"] for c in result["changes"]]
        assert "new.py" in paths

    @pytest.mark.asyncio
    async def test_scan_detects_modification(self, plugin, temp_dir):
        (temp_dir / "existing.py").write_text("original\n")
        await plugin.handle("watch", {})

        time.sleep(0.1)
        (temp_dir / "existing.py").write_text("modified\n")

        result = await plugin.handle("scan", {})
        assert result["success"] is True
        changes = [c for c in result["changes"] if c["path"] == "existing.py"]
        assert len(changes) >= 1
        assert changes[0]["type"] == "modified"

    @pytest.mark.asyncio
    async def test_scan_detects_deletion(self, plugin, temp_dir):
        (temp_dir / "to_delete.py").write_text("bye\n")
        await plugin.handle("watch", {})

        Path(temp_dir / "to_delete.py").unlink()

        result = await plugin.handle("scan", {})
        assert result["success"] is True
        changes = [c for c in result["changes"] if c["path"] == "to_delete.py"]
        assert len(changes) >= 1
        assert changes[0]["type"] == "deleted"

    @pytest.mark.asyncio
    async def test_get_changes(self, plugin, temp_dir):
        await plugin.handle("watch", {})
        (temp_dir / "a.py").write_text("a\n")
        await plugin.handle("scan", {})

        result = await plugin.handle("get_changes", {"limit": 10})
        assert result["success"] is True
        assert result["total"] >= 1
        assert len(result["changes"]) >= 1

    @pytest.mark.asyncio
    async def test_clear_changes(self, plugin, temp_dir):
        await plugin.handle("watch", {})
        (temp_dir / "b.py").write_text("b\n")
        await plugin.handle("scan", {})

        result = await plugin.handle("clear_changes", {})
        assert result["success"] is True
        assert result["cleared"] >= 1

        status = await plugin.handle("status", {})
        assert status["change_count"] == 0

    @pytest.mark.asyncio
    async def test_excludes_ignored_patterns(self, plugin, temp_dir):
        await plugin.handle("watch", {})
        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "__pycache__" / "cache.pyc").write_text("cache\n")

        result = await plugin.handle("scan", {})
        assert result["success"] is True
        pycache_changes = [c for c in result["changes"] if "__pycache__" in c["path"]]
        assert len(pycache_changes) == 0

    @pytest.mark.asyncio
    async def test_double_watch(self, plugin):
        await plugin.handle("watch", {})
        result = await plugin.handle("watch", {})
        assert result["success"] is True
        assert "already" in result["message"].lower()
