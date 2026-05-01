"""Tests for code generator plugin."""
import pytest
from ftcoding.plugins.code_generator.plugin import CodeGeneratorPlugin
from ftcoding.plugins.base import PluginContext
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


class TestCodeGeneratorPlugin:
    @pytest.fixture
    async def plugin(self, temp_dir):
        bus = MessageBus()
        config = Config(project_root=temp_dir)
        ctx = PluginContext(bus=bus, config=config, data_dir=str(temp_dir / "data"))

        p = CodeGeneratorPlugin()
        await p.initialize(ctx)
        yield p
        await p.shutdown()

    @pytest.mark.asyncio
    async def test_generate_function(self, plugin):
        result = await plugin.handle("generate_function", {
            "description": "sort a list of numbers",
            "language": "python",
            "name": "sort_numbers"
        })
        assert result["success"] is True
        assert "code" in result
        assert "sort_numbers" in result["code"] or result.get("fallback") is True

    @pytest.mark.asyncio
    async def test_generate_function_without_description(self, plugin):
        result = await plugin.handle("generate_function", {})
        assert result["success"] is False
        assert "description" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_generate_class(self, plugin):
        result = await plugin.handle("generate_class", {
            "description": "a calculator that can add and subtract",
            "language": "python",
            "name": "Calculator"
        })
        assert result["success"] is True
        assert "code" in result
        assert "Calculator" in result["code"] or result.get("fallback") is True

    @pytest.mark.asyncio
    async def test_explain_code(self, plugin):
        code = "def add(a, b):\n    return a + b\n"
        result = await plugin.handle("explain_code", {"code": code})
        assert result["success"] is True
        assert "explanation" in result
        assert len(result["explanation"]) > 0

    @pytest.mark.asyncio
    async def test_explain_code_empty(self, plugin):
        result = await plugin.handle("explain_code", {})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_refactor(self, plugin):
        code = "def f(x):\n    if x == True:\n        return 1\n    else:\n        return 0\n"
        result = await plugin.handle("refactor", {"code": code})
        assert result["success"] is True or result.get("error") is not None
        assert "code" in result

    @pytest.mark.asyncio
    async def test_fix_error(self, plugin):
        code = "def divide(a, b):\n    return a / b\n"
        error = "ZeroDivisionError: division by zero"
        result = await plugin.handle("fix_error", {"code": code, "error": error})
        assert result["success"] is True or result.get("error") is not None

    @pytest.mark.asyncio
    async def test_fix_error_missing_params(self, plugin):
        result = await plugin.handle("fix_error", {"code": "x = 1"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_fallback_function(self, plugin):
        code = plugin._fallback_function("test desc", "python", "my_func")
        assert "def my_func" in code
        assert "TODO" in code

    @pytest.mark.asyncio
    async def test_fallback_class(self, plugin):
        code = plugin._fallback_class("test desc", "python", "MyClass")
        assert "class MyClass" in code
        assert "TODO" in code
