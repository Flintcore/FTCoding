"""Code Editor Plugin - safe file operations and code generation."""
from __future__ import annotations
import difflib
from pathlib import Path
from typing import Optional
from ftcoding.plugins.base import Plugin, PluginContext


class CodeEditorPlugin(Plugin):
    """Plugin for safe code editing and generation."""

    name = "code_editor"
    version = "0.1.0"
    description = "File operations, diff/patch, and code generation"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx

    async def shutdown(self) -> None:
        pass

    async def handle(self, command: str, payload: dict) -> dict:
        handlers = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "generate_diff": self._generate_diff,
            "apply_diff": self._apply_diff,
            "edit_file": self._edit_file,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    async def _read_file(self, payload: dict) -> dict:
        """Read file content."""
        file_path = self._safe_path(payload.get("path", ""))
        if not file_path:
            return {"success": False, "error": "Invalid path"}

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {payload['path']}"}

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            start = payload.get("start_line", 0)
            end = payload.get("end_line", len(lines))

            selected = "\n".join(lines[start:end])
            return {
                "success": True,
                "content": selected,
                "total_lines": len(lines),
                "path": payload["path"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _write_file(self, payload: dict) -> dict:
        """Write content to file (creates or overwrites)."""
        file_path = self._safe_path(payload.get("path", ""))
        content = payload.get("content", "")
        backup = payload.get("backup", True)

        if not file_path:
            return {"success": False, "error": "Invalid path"}

        try:
            # Create backup if file exists
            if backup and file_path.exists():
                backup_path = Path(str(file_path) + ".backup")
                backup_path.write_text(file_path.read_text(), encoding="utf-8")

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "path": payload["path"],
                "bytes_written": len(content.encode("utf-8"))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _generate_diff(self, payload: dict) -> dict:
        """Generate unified diff between old and new content."""
        old = payload.get("old", "")
        new = payload.get("new", "")
        filename = payload.get("filename", "file.txt")

        diff = list(difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=filename,
            tofile=filename
        ))

        return {
            "success": True,
            "diff": "".join(diff)
        }

    async def _apply_diff(self, payload: dict) -> dict:
        """Apply a unified diff to a file."""
        file_path = self._safe_path(payload.get("path", ""))
        diff_text = payload.get("diff", "")

        if not file_path or not file_path.exists():
            return {"success": False, "error": "File not found"}

        try:
            original = file_path.read_text(encoding="utf-8")
            lines = original.splitlines(keepends=True)

            result_lines = self._parse_and_apply_diff(lines, diff_text)
            new_content = "".join(result_lines)

            # Backup
            backup_path = Path(str(file_path) + ".backup")
            backup_path.write_text(original, encoding="utf-8")

            file_path.write_text(new_content, encoding="utf-8")

            return {
                "success": True,
                "path": payload["path"],
                "lines_changed": len(result_lines) - len(lines)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _edit_file(self, payload: dict) -> dict:
        """Edit a specific line range in a file."""
        file_path = self._safe_path(payload.get("path", ""))
        start_line = payload.get("start_line", 0)
        end_line = payload.get("end_line")
        replacement = payload.get("replacement", "")

        if not file_path or not file_path.exists():
            return {"success": False, "error": "File not found"}

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            if end_line is None:
                end_line = start_line + 1

            # Backup
            backup_path = Path(str(file_path) + ".backup")
            backup_path.write_text(content, encoding="utf-8")

            new_lines = lines[:start_line] + replacement.split("\n") + lines[end_line:]
            file_path.write_text("\n".join(new_lines), encoding="utf-8")

            return {
                "success": True,
                "path": payload["path"],
                "lines_replaced": end_line - start_line
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _safe_path(self, rel_path: str) -> Optional[Path]:
        """Resolve relative path safely, preventing path traversal."""
        if not rel_path:
            return None

        root = self.ctx.config.project_root.resolve()
        target = (root / rel_path).resolve()

        try:
            target.relative_to(root)
            return target
        except ValueError:
            return None

    def _parse_and_apply_diff(self, lines: list[str], diff_text: str) -> list[str]:
        """Parse unified diff and apply to lines."""
        diff_lines = diff_text.splitlines(keepends=False)
        result = []
        i = 0
        in_hunk = False

        for dline in diff_lines:
            if dline.startswith("@@"):
                in_hunk = True
                continue
            if not in_hunk:
                continue

            if dline.startswith("-") and not dline.startswith("---"):
                if i < len(lines):
                    i += 1
            elif dline.startswith("+") and not dline.startswith("+++"):
                result.append(dline[1:] + "\n")
            elif dline.startswith(" "):
                if i < len(lines):
                    result.append(lines[i])
                    i += 1
            elif dline == "":
                if i < len(lines):
                    result.append(lines[i])
                    i += 1

        while i < len(lines):
            result.append(lines[i])
            i += 1

        return result
