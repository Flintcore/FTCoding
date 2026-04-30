"""Tests for kernel orchestrator."""
import pytest
from ftcoding.kernel.kernel import Kernel
from ftcoding.kernel.config import Config


class TestKernel:
    @pytest.fixture
    def config(self, temp_dir):
        return Config(project_root=temp_dir, memory_db_path=str(temp_dir / "memory.db"))

    @pytest.mark.asyncio
    async def test_kernel_initialization(self, config):
        kernel = Kernel(config)
        await kernel.initialize()
        assert kernel.bus is not None
        assert kernel.plugin_manager is not None
        assert kernel.memory is not None
        await kernel.shutdown()

    @pytest.mark.asyncio
    async def test_kernel_shutdown(self, config):
        kernel = Kernel(config)
        await kernel.initialize()
        await kernel.shutdown()
        assert kernel._initialized is False

    @pytest.mark.asyncio
    async def test_kernel_health(self, config):
        kernel = Kernel(config)
        await kernel.initialize()
        health = await kernel.health()
        assert "kernel" in health
        assert health["kernel"]["status"] == "healthy"
        await kernel.shutdown()
