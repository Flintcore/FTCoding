"""Tests for dependency analyzer plugin."""
import pytest
import json
from pathlib import Path
from ftcoding.plugins.dependency_analyzer.plugin import DependencyAnalyzerPlugin
from ftcoding.plugins.base import PluginContext
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


class TestDependencyAnalyzerPlugin:
    @pytest.fixture
    async def plugin(self, temp_dir):
        bus = MessageBus()
        config = Config(project_root=temp_dir)
        ctx = PluginContext(bus=bus, config=config, data_dir=str(temp_dir / "data"))

        p = DependencyAnalyzerPlugin()
        await p.initialize(ctx)
        yield p
        await p.shutdown()

    @pytest.mark.asyncio
    async def test_analyze_no_deps(self, plugin, temp_dir):
        result = await plugin.handle("analyze", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result.get("results") == []

    @pytest.mark.asyncio
    async def test_analyze_python_pyproject(self, plugin, temp_dir):
        (temp_dir / "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = ["requests>=2.0", "pytest"]\n'
        )
        result = await plugin.handle("analyze", {"path": str(temp_dir)})
        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["type"] == "python"

    @pytest.mark.asyncio
    async def test_analyze_python_requirements(self, plugin, temp_dir):
        (temp_dir / "requirements.txt").write_text("requests==2.31.0\npytest>=7.0\n")
        result = await plugin.handle("analyze_python", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result["dependency_count"] == 2
        deps = {d["name"]: d for d in result["dependencies"]}
        assert "requests" in deps
        assert deps["requests"]["version"] == "2.31.0"
        assert "pytest" in deps

    @pytest.mark.asyncio
    async def test_analyze_javascript(self, plugin, temp_dir):
        pkg = {
            "name": "test-app",
            "version": "1.0.0",
            "dependencies": {"lodash": "^4.17.20"},
            "devDependencies": {"jest": "^29.0.0"}
        }
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        result = await plugin.handle("analyze_javascript", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result["dependency_count"] == 2
        deps = {d["name"]: d for d in result["dependencies"]}
        assert "lodash" in deps
        assert "jest" in deps
        assert deps["lodash"]["version"] == "4.17.20"

    @pytest.mark.asyncio
    async def test_analyze_go(self, plugin, temp_dir):
        (temp_dir / "go.mod").write_text("module example.com/test\n\ngo 1.21\n\nrequire github.com/gin-gonic/gin v1.9.1\n")

        result = await plugin.handle("analyze_go", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result["go_version"] == "1.21"
        deps = {d["name"]: d for d in result["dependencies"]}
        assert "github.com/gin-gonic/gin" in deps
        assert deps["github.com/gin-gonic/gin"]["version"] == "v1.9.1"

    @pytest.mark.asyncio
    async def test_parse_python_requirement(self, plugin):
        cases = [
            ("requests", {"name": "requests", "version": "", "operator": ""}),
            ("requests==2.31.0", {"name": "requests", "version": "2.31.0", "operator": "=="}),
            ("requests>=2.0", {"name": "requests", "version": "2.0", "operator": ">="}),
            ("pytest[extra]>=7.0", {"name": "pytest", "version": "7.0", "operator": ">="}),
        ]
        for raw, expected in cases:
            parsed = plugin._parse_python_requirement(raw)
            assert parsed is not None
            assert parsed["name"] == expected["name"]
            assert parsed["operator"] == expected["operator"]

    @pytest.mark.asyncio
    async def test_check_vulnerabilities(self, plugin, temp_dir):
        (temp_dir / "requirements.txt").write_text("requests==2.19.0\n")

        result = await plugin.handle("check_vulnerabilities", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result["scan_completed"] is True
        assert len(result["findings"]) >= 1

    @pytest.mark.asyncio
    async def test_check_vulnerabilities_js(self, plugin, temp_dir):
        pkg = {"name": "test", "dependencies": {"lodash": "4.17.19"}}
        (temp_dir / "package.json").write_text(json.dumps(pkg))

        result = await plugin.handle("check_vulnerabilities", {"path": str(temp_dir)})
        assert result["success"] is True
        lodash_findings = [f for f in result["findings"] if f["package"] == "lodash"]
        assert len(lodash_findings) >= 1

    @pytest.mark.asyncio
    async def test_analyze_multiple_types(self, plugin, temp_dir):
        (temp_dir / "pyproject.toml").write_text('[project]\ndependencies = []\n')
        (temp_dir / "package.json").write_text('{"name": "test"}')

        result = await plugin.handle("analyze", {"path": str(temp_dir)})
        assert result["success"] is True
        assert len(result["results"]) == 2
        types = [r["type"] for r in result["results"]]
        assert "python" in types
        assert "javascript" in types

    @pytest.mark.asyncio
    async def test_analyze_go_with_require_block(self, plugin, temp_dir):
        gomod = """module example.com/test

go 1.21

require (
	github.com/a/b v1.0.0
	github.com/c/d v2.0.0
)
"""
        (temp_dir / "go.mod").write_text(gomod)
        result = await plugin.handle("analyze_go", {"path": str(temp_dir)})
        assert result["success"] is True
        assert result["dependency_count"] == 2
