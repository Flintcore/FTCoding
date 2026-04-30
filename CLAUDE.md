# FTcoding - Claude Code Context

## Project Overview

FTcoding is a local-first Coding Agent for Chinese developers.
Core value: "数据不出网，越用越懂你的项目" (Data never leaves your network,
the more you use it, the more it understands your project).

## Architecture

- **Micro-kernel + Plugin system**
- Kernel: `src/ftcoding/kernel/` - bus, plugin manager, config, LLM gateway, cron
- Plugins: `src/ftcoding/plugins/` - independent functional units
  - `code_insight`: AST parsing, indexing, RAG search
  - `code_editor`: File ops, diff/patch, code generation
  - `execution_env`: Safe command execution, test runner
- Memory: `src/ftcoding/memory/` - SQLite preference/pattern storage
- CLI: `src/ftcoding/cli/` - Interactive terminal (Click + Rich)
- IDE Bridge: `src/ftcoding/ide_bridge/` - FastAPI HTTP/WebSocket

## Key Patterns

### Adding a New Plugin

1. Create directory under `src/ftcoding/plugins/<name>/`
2. Inherit from `ftcoding.plugins.base.Plugin`
3. Implement `initialize()`, `shutdown()`, `handle()`
4. Register in CLI (`cli/main.py`) and IDE bridge (`ide_bridge/server.py`)

### Message Bus Usage

```python
# Subscribe
ctx.bus.subscribe("topic.name", handler)

# Publish
await ctx.bus.publish("topic.name", {"key": "value"})

# Request/Response
result = await ctx.bus.request("topic.name", payload)
```

### Testing

- All new code must have tests in `tests/`
- Use pytest with asyncio support
- Target 80%+ coverage
- Run: `pytest`

## Development Commands

```bash
# Install dependencies
poetry install

# Run tests
pytest

# Run CLI
poetry run ftcoding

# Run IDE bridge
poetry run python -m ftcoding.ide_bridge.server

# Run self-iteration
poetry run ftcoding-cron
```

## Tech Stack

Python 3.11+, Poetry, Click, Rich, FastAPI, tree-sitter, Chroma, SQLite, LiteLLM, APScheduler
