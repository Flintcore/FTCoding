"""Project Scaffold Plugin - Initialize projects with best-practice structure."""
from __future__ import annotations
from pathlib import Path
from ftcoding.plugins.base import Plugin, PluginContext


class ProjectScaffoldPlugin(Plugin):
    """Plugin for scaffolding new projects with language-specific best practices."""

    name = "project_scaffold"
    version = "0.1.0"
    description = "Initialize projects with best-practice structure and configs"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.project_root = ctx.config.project_root

    async def shutdown(self) -> None:
        pass

    async def handle(self, command: str, payload: dict) -> dict:
        handlers = {
            "detect_type": self._detect_type,
            "init_python": self._init_python,
            "init_javascript": self._init_javascript,
            "init_go": self._init_go,
            "add_ci": self._add_ci,
            "add_docker": self._add_docker,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    async def _detect_type(self, payload: dict) -> dict:
        """Detect project type based on existing files."""
        root = Path(payload.get("path", self.project_root))

        indicators = {
            "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
            "javascript": ["package.json", "package-lock.json", "yarn.lock"],
            "typescript": ["tsconfig.json", "package.json"],
            "go": ["go.mod", "go.sum"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "java": ["pom.xml", "build.gradle"],
            "docker": ["Dockerfile", "docker-compose.yml"],
        }

        detected = []
        for ptype, files in indicators.items():
            for f in files:
                if (root / f).exists():
                    detected.append(ptype)
                    break

        if not detected:
            return {"success": True, "type": "unknown", "detected": []}

        return {"success": True, "type": detected[0], "detected": detected}

    async def _init_python(self, payload: dict) -> dict:
        """Initialize a Python project structure."""
        root = Path(payload.get("path", self.project_root))
        name = payload.get("name", "my_project")

        created = []

        # Directory structure
        dirs = [
            root / name.replace("-", "_"),
            root / "tests",
            root / "docs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d.relative_to(root)))

        # pyproject.toml
        pyproject = root / "pyproject.toml"
        if not pyproject.exists():
            pyproject.write_text(f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = ""
readme = "README.md"
license = {{text = "MIT"}}
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest", "black", "ruff", "mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
""")
            created.append("pyproject.toml")

        # __init__.py
        init_file = root / name.replace("-", "_") / "__init__.py"
        if not init_file.exists():
            init_file.write_text(f'"""{name} package."""\n\n__version__ = "0.1.0"\n')
            created.append(f"{name.replace('-', '_')}/__init__.py")

        # README.md
        readme = root / "README.md"
        if not readme.exists():
            readme.write_text(f"# {name}\n\n")
            created.append("README.md")

        # .gitignore
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("__pycache__/\n*.pyc\n.venv/\nvenv/\n.env\n")
            created.append(".gitignore")

        return {"success": True, "type": "python", "created": created}

    async def _init_javascript(self, payload: dict) -> dict:
        """Initialize a JavaScript/Node.js project structure."""
        root = Path(payload.get("path", self.project_root))
        name = payload.get("name", "my-project")

        created = []

        dirs = [
            root / "src",
            root / "tests",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d.relative_to(root)))

        # package.json
        pkg = root / "package.json"
        if not pkg.exists():
            pkg.write_text(f"""{{
  "name": "{name}",
  "version": "0.1.0",
  "description": "",
  "main": "src/index.js",
  "scripts": {{
    "test": "jest",
    "lint": "eslint src/"
  }},
  "devDependencies": {{
    "jest": "^29.0.0",
    "eslint": "^8.0.0"
  }}
}}
""")
            created.append("package.json")

        # src/index.js
        index = root / "src" / "index.js"
        if not index.exists():
            index.write_text("// Entry point\n")
            created.append("src/index.js")

        # README.md
        readme = root / "README.md"
        if not readme.exists():
            readme.write_text(f"# {name}\n\n")
            created.append("README.md")

        # .gitignore
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("node_modules/\n.env\ndist/\n")
            created.append(".gitignore")

        return {"success": True, "type": "javascript", "created": created}

    async def _init_go(self, payload: dict) -> dict:
        """Initialize a Go project structure."""
        root = Path(payload.get("path", self.project_root))
        module = payload.get("name", "example.com/user/project")

        created = []

        # go.mod
        gomod = root / "go.mod"
        if not gomod.exists():
            gomod.write_text(f"module {module}\n\ngo 1.21\n")
            created.append("go.mod")

        # main.go
        main = root / "main.go"
        if not main.exists():
            main.write_text("""package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
""")
            created.append("main.go")

        # README.md
        readme = root / "README.md"
        if not readme.exists():
            readme.write_text(f"# {module.split('/')[-1]}\n\n")
            created.append("README.md")

        return {"success": True, "type": "go", "created": created}

    async def _add_ci(self, payload: dict) -> dict:
        """Add GitHub Actions CI configuration."""
        root = Path(payload.get("path", self.project_root))
        ci_dir = root / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)

        # Detect project type for CI template
        detect = await self._detect_type({"path": str(root)})
        ptype = detect.get("type", "python")

        ci_file = ci_dir / "ci.yml"
        if ptype == "python":
            ci_file.write_text("""name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest
""")
        elif ptype in ("javascript", "typescript"):
            ci_file.write_text("""name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test
""")
        else:
            ci_file.write_text("""name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Add your test commands here"
""")

        return {"success": True, "created": [".github/workflows/ci.yml"]}

    async def _add_docker(self, payload: dict) -> dict:
        """Add Docker configuration."""
        root = Path(payload.get("path", self.project_root))
        created = []

        # Detect project type
        detect = await self._detect_type({"path": str(root)})
        ptype = detect.get("type", "python")

        dockerfile = root / "Dockerfile"
        if ptype == "python":
            dockerfile.write_text("""FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e "."

CMD ["python", "-m", "my_project"]
""")
        elif ptype in ("javascript", "typescript"):
            dockerfile.write_text("""FROM node:20-slim

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

CMD ["node", "src/index.js"]
""")
        else:
            dockerfile.write_text("""FROM alpine:latest

WORKDIR /app
COPY . .

CMD ["echo", "Hello, Docker!"]
""")

        created.append("Dockerfile")

        # docker-compose.yml
        compose = root / "docker-compose.yml"
        if not compose.exists():
            compose.write_text("""version: '3.8'
services:
  app:
    build: .
    volumes:
      - .:/app
""")
            created.append("docker-compose.yml")

        return {"success": True, "created": created}
