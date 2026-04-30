# FTcoding Design Document

## Project Overview

FTcoding is a local-first Coding Agent designed for Chinese developers. Core value proposition: **"数据不出网，越用越懂你的项目"** (Data never leaves your network, the more you use it, the more it understands your project).

- **License**: Apache 2.0
- **Repository**: https://github.com/Flintcore/FTCoding
- **Architecture**: Micro-kernel + Plugin system
- **Protocol**: Local HTTP/WebSocket for IDE integration, CLI for direct interaction

## Core Design Decisions

### 1. Micro-kernel + Plugin Architecture

The system is split into a lightweight core and independent plugins communicating via local message bus:

- **Kernel**: Message routing, plugin lifecycle, configuration, LLM gateway, cron scheduler
- **Plugins**: Self-contained functional units, each running in isolated process space
- **Benefit**: Each feature evolves independently; new capabilities are added by dropping in new plugins

### 2. Local-First Philosophy

- All code analysis happens locally via AST parsers (tree-sitter)
- Vector index stored in local SQLite/chroma
- User preference learning stored in local database
- LLM calls route through configurable local/remote gateway (default: local Ollama for privacy)

### 3. Self-Iterating Engine

Built-in cron mechanism triggers daily:
- Code health check (lint, test, coverage)
- New feature ideation based on project patterns
- Auto-generation of feature branches
- PR creation for human review (optional)

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FTcoding                             │
├─────────────────────────────────────────────────────────────┤
│  CLI Entry    │    IDE Bridge (HTTP/WebSocket)              │
├───────────────┴─────────────────────────────────────────────┤
│                      Kernel Core                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Message Bus │  │ Plugin Mgr   │  │ LLM Gateway         │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Config      │  │ Cron Engine  │  │ Memory Store (SQLite)│ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      Plugins                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Code Insight │ │ Code Editor  │ │ Execution Env        │ │
│  │ - AST parse  │ │ - File ops   │ │ - Sandbox exec       │ │
│  │ - Vector idx │ │ - Diff/patch │ │ - Test runner        │ │
│  │ - RAG search │ │ - Refactor   │ │ - Error capture      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Component Specifications

### Kernel Core

**Message Bus**: Async pub/sub using Python asyncio. Plugins subscribe to topics, kernel routes messages.

**Plugin Manager**: Discovers plugins from `plugins/` directory, manages lifecycle (load/start/stop/reload), handles crashes gracefully.

**LLM Gateway**: Unified interface for LLM calls. Supports:
- Local: Ollama, llama.cpp
- Remote: OpenAI-compatible APIs (user-configurable)
- Streaming responses

**Cron Engine**: Python schedule/celery beat. Daily tasks:
- `health_check`: Run tests, lint, check coverage
- `ideate_feature`: Analyze project patterns, propose new plugin/feature
- `update_dependencies`: Check for security updates

**Memory Store**: SQLite with tables:
- `user_preferences`: Coding style, naming conventions, tab width
- `project_patterns`: Common file structures, import patterns
- `interaction_history`: Past commands and outcomes for context

### Plugin: Code Insight

Purpose: Understand project structure and retrieve relevant context.

Capabilities:
- Parse source files (Python, JavaScript, TypeScript, Go, Rust, Java) via tree-sitter
- Build vector index of functions, classes, documentation
- RAG search: Given query, retrieve most relevant code snippets
- Dependency graph analysis

Data flow:
1. Watch filesystem for changes
2. Incrementally update AST and vector index
3. Serve search queries from other plugins

### Plugin: Code Editor

Purpose: Safely modify code.

Capabilities:
- Read/write files with backup/rollback
- Generate unified diffs for review
- Apply patches atomically
- Refactoring: rename, extract function, move code
- Code generation from natural language prompts

Safety:
- All changes staged in temp directory first
- User confirmation required for destructive operations
- Git integration: auto-commit with descriptive messages

### Plugin: Execution Environment

Purpose: Run commands and tests safely.

Capabilities:
- Execute shell commands in sandboxed environment
- Run test suites and capture results
- Parse error output and suggest fixes
- Environment setup (dependencies, virtualenv)

Safety:
- Block dangerous commands (rm -rf /, format disk, etc.)
- Timeout on long-running commands
- Resource limits (CPU, memory)

## Data Flow

### User Request Flow

```
User Input → CLI/IDE Bridge → Kernel Message Bus → Relevant Plugins
                                                      ↓
Response ←  Kernel  ←  Plugin Results Aggregation  ←─┘
```

### Learning Flow (Background)

```
File Change → Code Insight updates index
User Action → Memory Store updates preference
Daily Cron  → Analyze patterns → Update user model
```

## Error Handling

- Plugin crash: Kernel detects, restarts plugin, logs incident, notifies user
- LLM unavailable: Fallback to local model, queue remote requests
- File operation failure: Atomic rollback, preserve previous state
- Command timeout: Kill process, return partial output with warning

## Testing Strategy

- Unit tests: Each plugin independently tested
- Integration tests: Kernel + plugin communication
- E2E tests: CLI commands against sample projects
- Coverage target: 80%+

## Today's Implementation Scope (v0.1.0)

1. **Project scaffold**: Python project with poetry/pip, directory structure
2. **Kernel core**: Message bus, plugin manager, config system
3. **Code Insight plugin**: Basic AST parsing, file watching, simple search
4. **Code Editor plugin**: File read/write, diff generation, patch apply
5. **Execution Environment plugin**: Command execution with safety checks
6. **CLI interface**: Interactive terminal UI (rich/click)
7. **Memory system**: SQLite schema, preference recording
8. **Self-iteration setup**: Cron configuration, daily check script
9. **CLAUDE.md**: Project documentation initialized
10. **GitHub push**: Complete repository setup

## Future Plugins (Post v0.1.0)

- Git workflow plugin (commit, branch, PR)
- Documentation plugin (auto-generate docs)
- Test generation plugin
- IDE extensions (VS Code, JetBrains)
- Multi-language support enhancement
- Team collaboration features

## Tech Stack

- **Language**: Python 3.11+
- **CLI**: Click + Rich (terminal UI)
- **HTTP**: FastAPI (IDE bridge)
- **AST**: Tree-sitter
- **Vector DB**: Chroma (local)
- **DB**: SQLite (user data)
- **LLM**: LiteLLM (unified gateway)
- **Scheduling**: APScheduler
- **Testing**: pytest
- **Packaging**: Poetry
