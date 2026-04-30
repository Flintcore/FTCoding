"""Tests for plugin manager."""
import pytest
from ftcoding.kernel.plugin_manager import PluginManager
from ftcoding.plugins.base import Plugin, PluginContext
from ftcoding.kernel.bus import MessageBus


class MockPlugin(Plugin):
    """Test plugin implementation."""
    name = "mock"
    version = "0.1.0"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.initialized = True

    async def shutdown(self) -> None:
        self.initialized = False

    async def handle(self, topic: str, payload: dict) -> dict:
        return {"handled": True, "topic": topic}


class TestPluginManager:
    def test_register_plugin(self):
        bus = MessageBus()
        mgr = PluginManager(bus)
        plugin = MockPlugin()

        mgr.register(plugin)
        assert "mock" in mgr.list_plugins()

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        bus = MessageBus()
        mgr = PluginManager(bus)
        plugin = MockPlugin()

        mgr.register(plugin)
        await mgr.initialize_all()

        assert plugin.initialized is True

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        bus = MessageBus()
        mgr = PluginManager(bus)
        plugin = MockPlugin()

        mgr.register(plugin)
        await mgr.initialize_all()
        await mgr.shutdown_all()

        assert plugin.initialized is False

    def test_get_plugin(self):
        bus = MessageBus()
        mgr = PluginManager(bus)
        plugin = MockPlugin()

        mgr.register(plugin)
        retrieved = mgr.get_plugin("mock")

        assert retrieved is plugin
