"""Plugin lifecycle management."""
from __future__ import annotations
from typing import Optional
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config
from ftcoding.plugins.base import Plugin, PluginContext


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""

    def __init__(self, bus: MessageBus, config: Optional[Config] = None):
        self.bus = bus
        self.config = config or Config()
        self._plugins: dict[str, Plugin] = {}
        self._contexts: dict[str, PluginContext] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance."""
        if not plugin.name:
            raise ValueError("Plugin must have a name")
        self._plugins[plugin.name] = plugin

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        """List all registered plugin names."""
        return list(self._plugins.keys())

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        if name in self._plugins:
            del self._plugins[name]

    async def initialize_all(self) -> None:
        """Initialize all registered plugins."""
        for name, plugin in self._plugins.items():
            ctx = PluginContext(
                bus=self.bus,
                config=self.config,
                data_dir=f".ftcoding/plugins/{name}"
            )
            self._contexts[name] = ctx
            await plugin.initialize(ctx)

    async def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in self._plugins.values():
            await plugin.shutdown()
        self._plugins.clear()
        self._contexts.clear()

    async def health_check(self) -> dict[str, dict]:
        """Check health of all plugins."""
        return {name: plugin.health() for name, plugin in self._plugins.items()}
