"""Execution Environment Plugin - safe command execution."""
from __future__ import annotations
import asyncio
import shlex
import os
from pathlib import Path
from typing import Optional
from ftcoding.plugins.base import Plugin, PluginContext


class ExecutionEnvPlugin(Plugin):
    """Plugin for safely executing commands and tests."""

    name = "execution_env"
    version = "0.1.0"
    description = "Sandboxed command execution and test running"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx

    async def shutdown(self) -> None:
        pass

    async def handle(self, command: str, payload: dict) -> dict:
        handlers = {
            "execute": self._execute,
            "run_tests": self._run_tests,
            "check_command": self._check_command,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    async def _execute(self, payload: dict) -> dict:
        """Execute a shell command safely."""
        command = payload.get("command", "")
        timeout = payload.get("timeout", 30.0)
        cwd = payload.get("cwd", str(self.ctx.config.project_root))

        if not command:
            return {"success": False, "error": "No command provided"}

        # Safety check
        check = self._is_safe(command)
        if not check["safe"]:
            return {
                "success": False,
                "error": f"Command blocked: {check['reason']}"
            }

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s"
                }

            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "command": command
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_tests(self, payload: dict) -> dict:
        """Run test suite."""
        path = payload.get("path", ".")
        runner = payload.get("runner", "pytest")
        timeout = payload.get("timeout", 120.0)

        if runner == "pytest":
            cmd = f"pytest {path} -v"
        elif runner == "unittest":
            cmd = f"python -m unittest discover {path}"
        elif runner == "jest":
            cmd = f"jest {path}"
        else:
            return {"success": False, "error": f"Unknown test runner: {runner}"}

        return await self._execute({
            "command": cmd,
            "timeout": timeout,
            "cwd": payload.get("cwd", str(self.ctx.config.project_root))
        })

    async def _check_command(self, payload: dict) -> dict:
        """Check if a command is safe without executing."""
        command = payload.get("command", "")
        check = self._is_safe(command)
        return {"safe": check["safe"], "reason": check.get("reason", "")}

    def _is_safe(self, command: str) -> dict:
        """Check if command passes safety checks."""
        command_lower = command.lower()

        # Check blocked patterns
        for blocked in self.ctx.config.blocked_commands:
            if blocked.lower() in command_lower:
                return {"safe": False, "reason": f"Contains blocked pattern: {blocked}"}

        # Check for dangerous patterns
        dangerous_patterns = [
            "rm -rf /", "rm -rf /*", "mkfs", "dd if=",
            ":(){ :|:& };:", "> /dev/sda",
            "curl.*|.*sh", "wget.*|.*sh"
        ]
        for pattern in dangerous_patterns:
            if pattern.replace(".*", "").lower() in command_lower:
                return {"safe": False, "reason": "Dangerous pattern detected"}

        # Parse first token
        try:
            tokens = shlex.split(command)
            if not tokens:
                return {"safe": False, "reason": "Empty command"}

            first_token = tokens[0].lower()

            # Check if command is in safe list or is a known binary
            safe_cmds = [c.lower() for c in self.ctx.config.safe_commands]
            if first_token not in safe_cmds:
                # Allow if it's a path to a known binary
                if not (first_token.startswith("./") or first_token.startswith("../")):
                    return {"safe": False, "reason": f"Command '{first_token}' not in safe list"}

        except ValueError:
            return {"safe": False, "reason": "Could not parse command"}

        return {"safe": True}
