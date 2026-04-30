"""Tests for code editor plugin."""
import pytest
from ftcoding.plugins.code_editor.plugin import CodeEditorPlugin
from ftcoding.plugins.base import PluginContext
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


class TestCodeEditorPlugin:
    @pytest.fixture
    async def plugin(self, temp_dir):
        bus = MessageBus()
        config = Config(project_root=temp_dir)
        ctx = PluginContext(bus=bus, config=config, data_dir=str(temp_dir / "data"))

        p = CodeEditorPlugin()
        await p.initialize(ctx)
        yield p
        await p.shutdown()

    @pytest.mark.asyncio
    async def test_read_file(self, plugin, temp_dir):
        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1\ny = 2\n")

        result = await plugin.handle("read_file", {"path": "test.py"})
        assert result["success"] is True
        assert "x = 1" in result["content"]

    @pytest.mark.asyncio
    async def test_write_file(self, plugin, temp_dir):
        result = await plugin.handle("write_file", {
            "path": "new.py",
            "content": "print('hello')\n"
        })
        assert result["success"] is True
        assert (temp_dir / "new.py").exists()

    @pytest.mark.asyncio
    async def test_generate_diff(self, plugin):
        old = "line1\nline2\nline3\n"
        new = "line1\nmodified\nline3\n"

        result = await plugin.handle("generate_diff", {"old": old, "new": new})
        assert result["success"] is True
        assert "-line2" in result["diff"]
        assert "+modified" in result["diff"]

    @pytest.mark.asyncio
    async def test_apply_diff(self, plugin, temp_dir):
        original = "line1\nline2\nline3\n"
        test_file = temp_dir / "patch.py"
        test_file.write_text(original)

        diff = """--- patch.py
+++ patch.py
@@ -1,3 +1,3 @@
 line1
-line2
+modified
 line3
"""

        result = await plugin.handle("apply_diff", {
            "path": "patch.py",
            "diff": diff
        })
        assert result["success"] is True
        content = (temp_dir / "patch.py").read_text()
        assert "modified" in content
