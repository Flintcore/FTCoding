"""Tests for memory store."""
import pytest
from ftcoding.memory.store import MemoryStore


class TestMemoryStore:
    @pytest.fixture
    def store(self, temp_dir):
        db_path = temp_dir / "test_memory.db"
        return MemoryStore(str(db_path))

    def test_record_preference(self, store):
        store.record_preference("tab_width", "4")
        value = store.get_preference("tab_width")
        assert value == "4"

    def test_update_preference(self, store):
        store.record_preference("tab_width", "4")
        store.record_preference("tab_width", "2")
        value = store.get_preference("tab_width")
        assert value == "2"

    def test_record_interaction(self, store):
        store.record_interaction("/analyze", "analyzed src/", success=True)
        history = store.get_recent_interactions(limit=1)
        assert len(history) == 1
        assert history[0]["command"] == "/analyze"

    def test_learn_pattern(self, store):
        store.learn_pattern("project_structure", "src/{module}/**/*.py")
        patterns = store.get_patterns("project_structure")
        assert len(patterns) >= 1

    def test_get_nonexistent_preference(self, store):
        value = store.get_preference("nonexistent")
        assert value is None
