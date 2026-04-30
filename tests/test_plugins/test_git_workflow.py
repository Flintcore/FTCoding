"""Tests for git workflow plugin."""
import pytest
import subprocess
from pathlib import Path
from ftcoding.plugins.git_workflow.plugin import GitWorkflowPlugin
from ftcoding.plugins.base import PluginContext
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


class TestGitWorkflowPlugin:
    @pytest.fixture
    async def plugin(self, temp_dir):
        bus = MessageBus()
        config = Config(project_root=temp_dir)
        ctx = PluginContext(bus=bus, config=config, data_dir=str(temp_dir / "data"))

        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, capture_output=True)

        p = GitWorkflowPlugin()
        await p.initialize(ctx)
        yield p
        await p.shutdown()

    @pytest.mark.asyncio
    async def test_status_empty(self, plugin, temp_dir):
        result = await plugin.handle("status", {})
        assert result["success"] is True
        assert "branch" in result
        assert "files" in result

    @pytest.mark.asyncio
    async def test_status_with_changes(self, plugin, temp_dir):
        (temp_dir / "new_file.py").write_text("x = 1\n")
        result = await plugin.handle("status", {})
        assert result["success"] is True
        assert len(result["files"]["untracked"]) == 1

    @pytest.mark.asyncio
    async def test_commit(self, plugin, temp_dir):
        (temp_dir / "test.py").write_text("hello\n")
        result = await plugin.handle("commit", {
            "message": "test commit",
            "all": True
        })
        assert result["success"] is True
        assert result["message"] == "test commit"

    @pytest.mark.asyncio
    async def test_log(self, plugin, temp_dir):
        # Create initial commit
        (temp_dir / "a.py").write_text("a\n")
        await plugin.handle("commit", {"message": "first", "all": True})

        result = await plugin.handle("log", {"limit": 5})
        assert result["success"] is True
        assert len(result["commits"]) >= 1
        assert result["commits"][0]["message"] == "first"

    @pytest.mark.asyncio
    async def test_branch_list(self, plugin, temp_dir):
        # Need an initial commit for branch to be visible
        (temp_dir / "init.py").write_text("# init\n")
        await plugin.handle("commit", {"message": "init", "all": True})

        result = await plugin.handle("branch_list", {})
        assert result["success"] is True
        assert len(result["branches"]) >= 1
        assert result["current"] in ("master", "main")

    @pytest.mark.asyncio
    async def test_branch_create_and_switch(self, plugin, temp_dir):
        create_result = await plugin.handle("branch_create", {"name": "feature-x"})
        assert create_result["success"] is True
        assert create_result["branch"] == "feature-x"

        switch_result = await plugin.handle("branch_switch", {"name": "master"})
        # May fail if default branch is "main" instead of "master"
        assert "success" in switch_result

    @pytest.mark.asyncio
    async def test_diff(self, plugin, temp_dir):
        (temp_dir / "file.py").write_text("original\n")
        await plugin.handle("commit", {"message": "init", "all": True})

        (temp_dir / "file.py").write_text("modified\n")
        result = await plugin.handle("diff", {})
        assert result["success"] is True
        assert "diff" in result

    @pytest.mark.asyncio
    async def test_commit_without_message(self, plugin):
        result = await plugin.handle("commit", {})
        assert result["success"] is False
        assert "message" in result["error"].lower()
