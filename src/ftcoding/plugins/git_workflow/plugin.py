"""Git Workflow Plugin - Git operations integrated with FTcoding."""
from __future__ import annotations
import subprocess
import os
from pathlib import Path
from ftcoding.plugins.base import Plugin, PluginContext


class GitWorkflowPlugin(Plugin):
    """Plugin for Git operations: status, diff, log, commit, branch."""

    name = "git_workflow"
    version = "0.1.0"
    description = "Git status, diff, log, commit, and branch operations"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.project_root = ctx.config.project_root

    async def shutdown(self) -> None:
        pass

    async def handle(self, command: str, payload: dict) -> dict:
        handlers = {
            "status": self._status,
            "diff": self._diff,
            "log": self._log,
            "commit": self._commit,
            "branch_list": self._branch_list,
            "branch_create": self._branch_create,
            "branch_switch": self._branch_switch,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    def _run_git(self, args: list[str], cwd: str | None = None) -> dict:
        """Execute a git command and return structured result."""
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace"
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except FileNotFoundError:
            return {"success": False, "error": "Git not found. Please install git."}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _status(self, payload: dict) -> dict:
        """Get git status."""
        result = self._run_git(["status", "--short", "--branch"])
        if not result["success"]:
            return result

        # Parse status output
        files = {"modified": [], "added": [], "deleted": [], "untracked": [], "renamed": []}
        branch = ""

        for line in result["stdout"].strip().split("\n"):
            if not line:
                continue
            if line.startswith("##"):
                branch = line[3:].strip()
                continue

            status_code = line[:2]
            file_path = line[3:].strip()

            if "D" in status_code:
                files["deleted"].append(file_path)
            elif "A" in status_code:
                files["added"].append(file_path)
            elif "R" in status_code:
                files["renamed"].append(file_path)
            elif "M" in status_code or "m" in status_code:
                files["modified"].append(file_path)
            elif "?" in status_code:
                files["untracked"].append(file_path)

        return {
            "success": True,
            "branch": branch,
            "files": files,
            "raw": result["stdout"]
        }

    async def _diff(self, payload: dict) -> dict:
        """Get git diff."""
        args = ["diff"]
        if payload.get("staged"):
            args.append("--cached")
        if payload.get("file"):
            args.append("--")
            args.append(payload["file"])

        result = self._run_git(args)
        return {
            "success": result["success"],
            "diff": result.get("stdout", ""),
            "error": result.get("error", "") or result.get("stderr", "")
        }

    async def _log(self, payload: dict) -> dict:
        """Get git log."""
        limit = payload.get("limit", 10)
        result = self._run_git([
            "log",
            f"-{limit}",
            "--pretty=format:%h|%an|%ad|%s",
            "--date=short"
        ])

        if not result["success"]:
            return result

        commits = []
        for line in result["stdout"].strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })

        return {
            "success": True,
            "commits": commits,
            "raw": result["stdout"]
        }

    async def _commit(self, payload: dict) -> dict:
        """Create a git commit."""
        message = payload.get("message", "")
        if not message:
            return {"success": False, "error": "Commit message is required"}

        # Stage files if specified
        files = payload.get("files", [])
        if files:
            add_result = self._run_git(["add"] + files)
            if not add_result["success"]:
                return add_result
        elif payload.get("all", False):
            add_result = self._run_git(["add", "-A"])
            if not add_result["success"]:
                return add_result

        # Create commit
        result = self._run_git(["commit", "-m", message])

        if result["success"]:
            return {
                "success": True,
                "message": message,
                "output": result["stdout"]
            }
        else:
            return {
                "success": False,
                "error": result.get("stderr", result.get("error", "Commit failed"))
            }

    async def _branch_list(self, payload: dict) -> dict:
        """List git branches."""
        result = self._run_git(["branch", "-avv"])
        if not result["success"]:
            return result

        branches = []
        current = ""
        for line in result["stdout"].strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            is_current = line.startswith("*")
            name = line[1:].strip().split()[0] if is_current else line.split()[0]
            if is_current:
                current = name
            branches.append({
                "name": name,
                "current": is_current
            })

        return {
            "success": True,
            "branches": branches,
            "current": current
        }

    async def _branch_create(self, payload: dict) -> dict:
        """Create a new branch."""
        name = payload.get("name", "")
        if not name:
            return {"success": False, "error": "Branch name is required"}

        result = self._run_git(["checkout", "-b", name])
        return {
            "success": result["success"],
            "branch": name,
            "output": result.get("stdout", ""),
            "error": result.get("stderr", result.get("error", ""))
        }

    async def _branch_switch(self, payload: dict) -> dict:
        """Switch to a branch."""
        name = payload.get("name", "")
        if not name:
            return {"success": False, "error": "Branch name is required"}

        result = self._run_git(["checkout", name])
        return {
            "success": result["success"],
            "branch": name,
            "output": result.get("stdout", ""),
            "error": result.get("stderr", result.get("error", ""))
        }
