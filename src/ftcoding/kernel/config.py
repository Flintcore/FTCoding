"""Configuration management for FTcoding."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
import yaml


class Config(BaseModel):
    """FTcoding configuration."""

    project_root: Path = Field(default_factory=Path.cwd)
    llm_provider: str = Field(default="ollama")
    llm_model: str = Field(default="codellama")
    llm_api_base: Optional[str] = Field(default="http://localhost:11434")
    llm_api_key: Optional[str] = Field(default=None)

    vector_db_path: str = Field(default=".ftcoding/vectors")
    memory_db_path: str = Field(default=".ftcoding/memory.db")

    max_file_size_kb: int = Field(default=1024)
    exclude_patterns: list[str] = Field(default_factory=lambda: [
        "*.pyc", "__pycache__", ".git", ".venv", "venv",
        "node_modules", ".ftcoding", "*.min.js", "*.min.css"
    ])

    safe_commands: list[str] = Field(default_factory=lambda: [
        "python", "pytest", "npm", "yarn", "pip", "poetry",
        "cargo", "go", "git", "ls", "cat", "echo", "mkdir", "sleep"
    ])
    blocked_commands: list[str] = Field(default_factory=lambda: [
        "rm -rf /", "mkfs", "dd", "format", "> /dev/sda"
    ])

    cron_enabled: bool = Field(default=True)
    cron_hour: int = Field(default=9)
    cron_minute: int = Field(default=0)

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "project_root": str(self.project_root),
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_api_base": self.llm_api_base,
            "llm_api_key": self.llm_api_key,
            "vector_db_path": self.vector_db_path,
            "memory_db_path": self.memory_db_path,
            "max_file_size_kb": self.max_file_size_kb,
            "exclude_patterns": self.exclude_patterns,
            "safe_commands": self.safe_commands,
            "blocked_commands": self.blocked_commands,
            "cron_enabled": self.cron_enabled,
            "cron_hour": self.cron_hour,
            "cron_minute": self.cron_minute,
        }

    def save(self, path: Path) -> None:
        """Save config to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)


def load_config(path: Optional[Path] = None) -> Config:
    """Load config from file or create default."""
    if path is None:
        path = Path.cwd() / ".ftcoding" / "config.yaml"

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data:
            if "project_root" in data:
                data["project_root"] = Path(data["project_root"])
            return Config(**data)

    return Config()
