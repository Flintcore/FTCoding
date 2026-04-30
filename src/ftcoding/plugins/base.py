"""Base plugin interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from ftcoding.kernel.bus import MessageBus
from ftcoding.kernel.config import Config


@dataclass
class PluginContext:
    """Context passed to plugins during initialization."""
    bus: MessageBus
    config: Config
    data_dir: str


class Plugin(ABC):
    """Base class for all FTcoding plugins."""

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    async def initialize(self, ctx: PluginContext) -> None:
        """Called when plugin is loaded. Subscribe to topics here."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Called when plugin is unloaded. Clean up resources."""
        pass

    @abstractmethod
    async def handle(self, topic: str, payload: dict) -> dict:
        """Handle a direct request."""
        pass

    def health(self) -> dict:
        """Return plugin health status."""
        return {"status": "healthy", "name": self.name}
