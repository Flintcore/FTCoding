"""Shared pytest fixtures."""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, onexc=lambda f, p, e: None)


@pytest.fixture
def sample_python_project(temp_dir):
    """Create a sample Python project structure."""
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()

    main_file = temp_dir / "src" / "main.py"
    main_file.write_text("""
def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
""")

    test_file = temp_dir / "tests" / "test_main.py"
    test_file.write_text("""
from src.main import add, Calculator

def test_add():
    assert add(1, 2) == 3

def test_multiply():
    calc = Calculator()
    assert calc.multiply(2, 3) == 6
""")
    return temp_dir
