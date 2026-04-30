"""Code Insight Plugin - AST parsing, indexing, and RAG search."""
from __future__ import annotations
from pathlib import Path
from ftcoding.plugins.base import Plugin, PluginContext


class CodeInsightPlugin(Plugin):
    """Plugin for understanding code structure and retrieving context."""

    name = "code_insight"
    version = "0.1.0"
    description = "AST parsing, vector indexing, and code search"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.project_files: dict[str, dict] = {}
        self._indexed = False

        # Subscribe to file change events
        ctx.bus.subscribe("file.changed", self._on_file_changed)
        ctx.bus.subscribe("file.created", self._on_file_created)
        ctx.bus.subscribe("file.deleted", self._on_file_deleted)

    async def shutdown(self) -> None:
        self.project_files.clear()

    async def handle(self, command: str, payload: dict) -> dict:
        """Handle plugin commands."""
        handlers = {
            "index_project": self._index_project,
            "search_code": self._search_code,
            "get_structure": self._get_structure,
            "get_file_content": self._get_file_content,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    async def _index_project(self, payload: dict) -> dict:
        """Index all source files in a project."""
        path = payload.get("path", str(self.ctx.config.project_root))
        root = Path(path)

        if not root.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        indexed = 0
        for file_path in self._find_source_files(root):
            try:
                info = self._analyze_file(file_path, root)
                rel_path = str(file_path.relative_to(root))
                self.project_files[rel_path] = info
                indexed += 1
            except Exception:
                continue

        self._indexed = True

        # Learn project structure patterns
        structure = self._extract_structure()
        await self.ctx.bus.publish("memory.learn", {
            "category": "project_structure",
            "pattern": structure
        })

        return {
            "success": True,
            "files_indexed": indexed,
            "project_path": path
        }

    async def _search_code(self, payload: dict) -> dict:
        """Search for code matching query."""
        query = payload.get("query", "")
        if not query:
            return {"success": False, "error": "No query provided"}

        if not self._indexed:
            await self._index_project({})

        results = []
        query_terms = query.lower().split()

        for rel_path, info in self.project_files.items():
            score = 0
            content = info.get("content", "").lower()
            symbols = " ".join(info.get("symbols", [])).lower()

            for term in query_terms:
                if term in symbols:
                    score += 10
                if term in content:
                    score += 1
                if term in rel_path.lower():
                    score += 5

            if score > 0:
                results.append({
                    "file": rel_path,
                    "score": score,
                    "symbols": info.get("symbols", [])[:5],
                    "preview": info.get("content", "")[:200]
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return {"success": True, "results": results[:10]}

    async def _get_structure(self, payload: dict) -> dict:
        """Get project file structure."""
        path = payload.get("path", str(self.ctx.config.project_root))
        root = Path(path)

        structure = {"dirs": [], "files": []}
        for item in sorted(root.rglob("*")):
            if self._should_exclude(item):
                continue
            rel = str(item.relative_to(root))
            if item.is_dir():
                structure["dirs"].append(rel)
            else:
                structure["files"].append(rel)

        return {"success": True, "structure": structure}

    async def _get_file_content(self, payload: dict) -> dict:
        """Get content of a specific file."""
        file_path = payload.get("path", "")
        root = self.ctx.config.project_root
        full_path = root / file_path

        # Security: prevent path traversal
        try:
            full_path.resolve().relative_to(root.resolve())
        except ValueError:
            return {"success": False, "error": "Access denied"}

        if not full_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            content = full_path.read_text(encoding="utf-8")
            return {"success": True, "content": content, "path": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_source_files(self, root: Path) -> list[Path]:
        """Find all source files in project."""
        source_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".h"}
        files = []

        for ext in source_extensions:
            files.extend(root.rglob(f"*{ext}"))

        return [f for f in files if not self._should_exclude(f)]

    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded."""
        path_str = str(path)
        exclude = self.ctx.config.exclude_patterns
        return any(pattern in path_str for pattern in exclude)

    def _analyze_file(self, file_path: Path, root: Path) -> dict:
        """Analyze a source file."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")

        # Simple symbol extraction (enhanced versions will use tree-sitter)
        symbols = []
        lines = content.split("\n")

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def "):
                symbols.append(stripped.split("(")[0].replace("def ", ""))
            elif stripped.startswith("class "):
                symbols.append(stripped.split(":")[0].split("(")[0].replace("class ", ""))
            elif stripped.startswith("function "):
                symbols.append(stripped.split("(")[0].replace("function ", ""))

        return {
            "path": str(file_path.relative_to(root)),
            "content": content[:5000],
            "symbols": symbols,
            "line_count": len(lines),
            "size_bytes": len(content.encode("utf-8")),
        }

    def _extract_structure(self) -> str:
        """Extract common project structure patterns."""
        dirs = set()
        for path in self.project_files:
            parts = Path(path).parts
            if len(parts) > 1:
                dirs.add(parts[0])
        return "/".join(sorted(dirs))

    async def _on_file_changed(self, msg) -> None:
        """Handle file change event."""
        path = msg.payload.get("path", "")
        if path in self.project_files:
            full_path = self.ctx.config.project_root / path
            if full_path.exists():
                info = self._analyze_file(full_path, self.ctx.config.project_root)
                self.project_files[path] = info

    async def _on_file_created(self, msg) -> None:
        """Handle file creation event."""
        path = msg.payload.get("path", "")
        full_path = self.ctx.config.project_root / path
        if full_path.exists() and not self._should_exclude(full_path):
            info = self._analyze_file(full_path, self.ctx.config.project_root)
            rel_path = str(full_path.relative_to(self.ctx.config.project_root))
            self.project_files[rel_path] = info

    async def _on_file_deleted(self, msg) -> None:
        """Handle file deletion event."""
        path = msg.payload.get("path", "")
        if path in self.project_files:
            del self.project_files[path]
