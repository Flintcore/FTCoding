"""File Watcher Plugin - Monitor filesystem changes and auto-reindex."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Callable
from ftcoding.plugins.base import Plugin, PluginContext


class FileWatcherPlugin(Plugin):
    """Plugin for watching file system changes and triggering actions."""

    name = "file_watcher"
    version = "0.1.0"
    description = "Monitor filesystem changes and auto-reindex code"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self._watching = False
        self._changes: list[dict] = []
        self._max_changes = 1000
        self._last_scan: dict[str, float] = {}
        self._scan_interval = 2.0  # seconds

    async def shutdown(self) -> None:
        self._watching = False

    async def handle(self, command: str, payload: dict) -> dict:
        handlers = {
            "watch": self._watch,
            "unwatch": self._unwatch,
            "status": self._status,
            "get_changes": self._get_changes,
            "clear_changes": self._clear_changes,
            "scan": self._scan,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    async def _watch(self, payload: dict) -> dict:
        """Start watching the project directory."""
        if self._watching:
            return {"success": True, "message": "Already watching", "watching": True}

        self._watching = True
        self._changes = []
        self._last_scan = self._snapshot()

        return {
            "success": True,
            "message": f"Watching {self.ctx.config.project_root}",
            "watching": True,
            "exclude": self.ctx.config.exclude_patterns,
        }

    async def _unwatch(self, payload: dict) -> dict:
        """Stop watching."""
        was_watching = self._watching
        self._watching = False
        return {
            "success": True,
            "message": "Stopped watching" if was_watching else "Was not watching",
            "watching": False,
        }

    async def _status(self, payload: dict) -> dict:
        """Get watcher status."""
        return {
            "success": True,
            "watching": self._watching,
            "change_count": len(self._changes),
            "project_root": str(self.ctx.config.project_root),
        }

    async def _get_changes(self, payload: dict) -> dict:
        """Get list of detected changes."""
        limit = payload.get("limit", 50)
        since = payload.get("since")

        changes = self._changes
        if since:
            changes = [c for c in changes if c["timestamp"] > since]

        return {
            "success": True,
            "changes": changes[-limit:] if limit else changes,
            "total": len(self._changes),
        }

    async def _clear_changes(self, payload: dict) -> dict:
        """Clear change history."""
        count = len(self._changes)
        self._changes = []
        return {"success": True, "cleared": count}

    async def _scan(self, payload: dict) -> dict:
        """Manually scan for changes."""
        current = self._snapshot()
        changes = self._detect_changes(self._last_scan, current)

        for change in changes:
            self._record_change(change)

        self._last_scan = current

        # Notify code_insight to reindex changed files
        if changes and self.ctx.bus:
            for change in changes:
                if change["type"] in ("modified", "created"):
                    await self.ctx.bus.publish("file.changed", {
                        "path": change["path"],
                        "type": change["type"]
                    })
                elif change["type"] == "deleted":
                    await self.ctx.bus.publish("file.deleted", {
                        "path": change["path"]
                    })

        return {
            "success": True,
            "changes_detected": len(changes),
            "changes": changes,
        }

    def _snapshot(self) -> dict[str, float]:
        """Take a snapshot of all tracked files and their mtimes."""
        snapshot = {}
        root = self.ctx.config.project_root
        exclude = self.ctx.config.exclude_patterns

        try:
            for path in root.rglob("*"):
                if path.is_file() and not self._is_excluded(path, exclude):
                    try:
                        rel = str(path.relative_to(root))
                        snapshot[rel] = path.stat().st_mtime
                    except (OSError, ValueError):
                        continue
        except PermissionError:
            pass

        return snapshot

    def _detect_changes(self, old: dict[str, float], new: dict[str, float]) -> list[dict]:
        """Detect changes between two snapshots."""
        changes = []
        now = time.time()

        # New files
        for path, mtime in new.items():
            if path not in old:
                changes.append({
                    "path": path,
                    "type": "created",
                    "timestamp": now,
                })
            elif old[path] != mtime:
                changes.append({
                    "path": path,
                    "type": "modified",
                    "timestamp": now,
                })

        # Deleted files
        for path in old:
            if path not in new:
                changes.append({
                    "path": path,
                    "type": "deleted",
                    "timestamp": now,
                })

        return changes

    def _record_change(self, change: dict) -> None:
        """Record a change, maintaining max size."""
        self._changes.append(change)
        if len(self._changes) > self._max_changes:
            self._changes = self._changes[-self._max_changes:]

    def _is_excluded(self, path: Path, patterns: list[str]) -> bool:
        """Check if path matches exclude patterns."""
        path_str = str(path)
        return any(p in path_str for p in patterns)
