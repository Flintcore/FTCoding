"""Kernel orchestrator - central hub of FTcoding."""
from __future__ import annotations
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config
from ftcoding.kernel.plugin_manager import PluginManager
from ftcoding.memory.store import MemoryStore


class Kernel:
    """Central kernel that orchestrates all subsystems."""

    def __init__(self, config: Config):
        self.config = config
        self.bus = MessageBus()
        self.plugin_manager = PluginManager(self.bus, config)
        self.memory = MemoryStore(config.memory_db_path)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize kernel and all subsystems."""
        if self._initialized:
            return

        # Ensure project directories exist
        import os
        os.makedirs(self.config.vector_db_path, exist_ok=True)
        os.makedirs(".ftcoding/plugins", exist_ok=True)

        # Initialize all plugins
        await self.plugin_manager.initialize_all()

        self._initialized = True

    async def shutdown(self) -> None:
        """Gracefully shutdown kernel."""
        if not self._initialized:
            return

        await self.plugin_manager.shutdown_all()
        self._initialized = False

    async def health(self) -> dict:
        """Get system health status."""
        return {
            "kernel": {"status": "healthy", "initialized": self._initialized},
            "plugins": await self.plugin_manager.health_check(),
        }

    async def send_command(self, plugin_name: str, command: str, payload: dict) -> dict:
        """Send a command to a specific plugin."""
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return {"error": f"Plugin '{plugin_name}' not found"}
        return await plugin.handle(command, payload)
