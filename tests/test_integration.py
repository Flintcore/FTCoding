"""Integration tests for FTcoding."""
import pytest
from ftcoding.kernel.kernel import Kernel
from ftcoding.kernel.config import Config
from ftcoding.plugins.code_insight.plugin import CodeInsightPlugin
from ftcoding.plugins.code_editor.plugin import CodeEditorPlugin
from ftcoding.plugins.execution_env.plugin import ExecutionEnvPlugin


class TestIntegration:
    @pytest.fixture
    async def kernel(self, temp_dir):
        config = Config(
            project_root=temp_dir,
            memory_db_path=str(temp_dir / "memory.db"),
            vector_db_path=str(temp_dir / "vectors")
        )
        k = Kernel(config)
        await k.initialize()

        k.plugin_manager.register(CodeInsightPlugin())
        k.plugin_manager.register(CodeEditorPlugin())
        k.plugin_manager.register(ExecutionEnvPlugin())
        await k.plugin_manager.initialize_all()

        yield k
        await k.shutdown()

    @pytest.fixture
    def sample_project(self, temp_dir):
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "app.py").write_text("""
def hello():
    return "Hello, World!"

class App:
    def run(self):
        print(hello())
""")
        return temp_dir

    @pytest.mark.asyncio
    async def test_full_workflow(self, kernel, sample_project):
        """Test indexing, searching, reading, and editing."""
        # 1. Index project
        index_result = await kernel.send_command(
            "code_insight", "index_project", {"path": str(sample_project)}
        )
        assert index_result["success"] is True
        assert index_result["files_indexed"] >= 1

        # 2. Search code
        search_result = await kernel.send_command(
            "code_insight", "search_code", {"query": "hello world"}
        )
        assert search_result["success"] is True
        assert len(search_result["results"]) > 0

        # 3. Read file
        read_result = await kernel.send_command(
            "code_editor", "read_file", {"path": "src/app.py"}
        )
        assert read_result["success"] is True
        assert "hello" in read_result["content"].lower()

        # 4. Write file
        write_result = await kernel.send_command(
            "code_editor", "write_file",
            {"path": "src/new.py", "content": "x = 42\n"}
        )
        assert write_result["success"] is True
        assert (sample_project / "src" / "new.py").exists()

        # 5. Execute command
        exec_result = await kernel.send_command(
            "execution_env", "execute", {"command": "echo test"}
        )
        assert exec_result["success"] is True
        assert "test" in exec_result["stdout"]

    @pytest.mark.asyncio
    async def test_memory_learning(self, kernel):
        """Test that memory records preferences."""
        kernel.memory.record_preference("test_pref", "value123")
        assert kernel.memory.get_preference("test_pref") == "value123"

        kernel.memory.learn_pattern("test_cat", "pattern123")
        patterns = kernel.memory.get_patterns("test_cat")
        assert len(patterns) > 0
