"""Dependency Analyzer Plugin - Analyze project dependencies and suggest updates."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any
from ftcoding.plugins.base import Plugin, PluginContext


class DependencyAnalyzerPlugin(Plugin):
    """Plugin for analyzing project dependencies and detecting issues."""

    name = "dependency_analyzer"
    version = "0.1.0"
    description = "Analyze dependencies, detect outdated packages, and suggest updates"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.project_root = ctx.config.project_root

    async def shutdown(self) -> None:
        pass

    async def handle(self, command: str, payload: dict) -> dict:
        handlers = {
            "analyze": self._analyze,
            "analyze_python": self._analyze_python,
            "analyze_javascript": self._analyze_javascript,
            "analyze_go": self._analyze_go,
            "check_vulnerabilities": self._check_vulnerabilities,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    async def _analyze(self, payload: dict) -> dict:
        """Auto-detect project type and analyze dependencies."""
        root = Path(payload.get("path", self.project_root))

        results = []

        if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
            py_result = await self._analyze_python({"path": str(root)})
            if py_result.get("success"):
                results.append({"type": "python", "data": py_result})

        if (root / "package.json").exists():
            js_result = await self._analyze_javascript({"path": str(root)})
            if js_result.get("success"):
                results.append({"type": "javascript", "data": js_result})

        if (root / "go.mod").exists():
            go_result = await self._analyze_go({"path": str(root)})
            if go_result.get("success"):
                results.append({"type": "go", "data": go_result})

        if not results:
            return {"success": True, "message": "No dependency files found", "results": []}

        return {"success": True, "results": results}

    async def _analyze_python(self, payload: dict) -> dict:
        """Analyze Python dependencies from pyproject.toml or requirements.txt."""
        root = Path(payload.get("path", self.project_root))
        deps = []

        # Parse requirements.txt
        req_file = root / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                dep = self._parse_python_requirement(line)
                if dep:
                    deps.append(dep)

        # Parse pyproject.toml dependencies
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            # Simple regex extraction for dependencies array
            dep_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if dep_match:
                for line in dep_match.group(1).splitlines():
                    line = line.strip().strip(',').strip('"').strip("'")
                    if line and not line.startswith("#"):
                        dep = self._parse_python_requirement(line)
                        if dep:
                            deps.append(dep)

        return {
            "success": True,
            "language": "python",
            "dependency_count": len(deps),
            "dependencies": deps,
            "files_checked": [str(f) for f in [req_file, pyproject] if f.exists()],
        }

    def _parse_python_requirement(self, line: str) -> dict | None:
        """Parse a single Python requirement line."""
        # Handle formats: package, package==1.0, package>=1.0, package~=1.0, package[extra]
        match = re.match(r'^([a-zA-Z0-9_.-]+)(?:\[[^\]]+\])?\s*([<>=~!]+)?\s*(.*)?$', line)
        if not match:
            return None

        name = match.group(1)
        operator = match.group(2) or ""
        version = match.group(3) or "" if operator else ""
        # Clean up version
        version = version.strip().rstrip(';')

        return {
            "name": name,
            "version": version,
            "operator": operator,
            "raw": line,
            "outdated": None,  # Would need PyPI lookup for real check
        }

    async def _analyze_javascript(self, payload: dict) -> dict:
        """Analyze JavaScript dependencies from package.json."""
        root = Path(payload.get("path", self.project_root))
        pkg_file = root / "package.json"

        if not pkg_file.exists():
            return {"success": False, "error": "package.json not found"}

        try:
            data = json.loads(pkg_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid package.json: {e}"}

        deps = []
        for dep_type in ("dependencies", "devDependencies", "peerDependencies"):
            dep_dict = data.get(dep_type, {})
            for name, version in dep_dict.items():
                deps.append({
                    "name": name,
                    "version": version.lstrip("^~"),
                    "operator": "^" if version.startswith("^") else "~" if version.startswith("~") else "",
                    "type": dep_type,
                    "raw": f"{name}@{version}",
                })

        return {
            "success": True,
            "language": "javascript",
            "dependency_count": len(deps),
            "dependencies": deps,
            "name": data.get("name", "unknown"),
            "version": data.get("version", "unknown"),
        }

    async def _analyze_go(self, payload: dict) -> dict:
        """Analyze Go dependencies from go.mod."""
        root = Path(payload.get("path", self.project_root))
        gomod = root / "go.mod"

        if not gomod.exists():
            return {"success": False, "error": "go.mod not found"}

        content = gomod.read_text(encoding="utf-8")
        deps = []

        in_require_block = False
        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("require ("):
                in_require_block = True
                continue
            if stripped == ")" and in_require_block:
                in_require_block = False
                continue
            if stripped.startswith("require ") and not in_require_block:
                # Direct requirement: require module version
                parts = stripped[8:].strip().split()
                if len(parts) >= 2:
                    deps.append({
                        "name": parts[0],
                        "version": parts[1],
                        "operator": "",
                        "raw": f"{parts[0]} {parts[1]}",
                    })
            elif in_require_block and stripped:
                # Inside require block
                parts = stripped.split()
                if len(parts) >= 2 and not stripped.startswith("//"):
                    deps.append({
                        "name": parts[0],
                        "version": parts[1],
                        "operator": "",
                        "raw": f"{parts[0]} {parts[1]}",
                    })

        # Extract Go version
        go_version = ""
        for line in content.splitlines():
            if line.startswith("go "):
                go_version = line[3:].strip()
                break

        return {
            "success": True,
            "language": "go",
            "dependency_count": len(deps),
            "dependencies": deps,
            "go_version": go_version,
        }

    async def _check_vulnerabilities(self, payload: dict) -> dict:
        """Check for common vulnerability patterns in dependencies."""
        root = Path(payload.get("path", self.project_root))

        # Known vulnerable package patterns (simplified static check)
        known_issues = {
            "python": {
                "requests": [("<", "2.20.0", "CVE-2018-18074")],
                "django": [("<", "3.0.14", "CVE-2021-31542")],
                "flask": [("<", "1.0.0", "CVE-2018-1000656")],
            },
            "javascript": {
                "lodash": [("<", "4.17.21", "CVE-2021-23337")],
                "minimist": [("<", "1.2.6", "CVE-2021-44906")],
            },
        }

        findings = []

        # Check Python deps
        py_result = await self._analyze_python({"path": str(root)})
        if py_result.get("success"):
            for dep in py_result.get("dependencies", []):
                name = dep["name"].lower()
                if name in known_issues.get("python", {}):
                    for op, vuln_version, cve in known_issues["python"][name]:
                        findings.append({
                            "package": dep["name"],
                            "version": dep["version"],
                            "issue": cve,
                            "severity": "high",
                            "language": "python",
                        })

        # Check JS deps
        js_result = await self._analyze_javascript({"path": str(root)})
        if js_result.get("success"):
            for dep in js_result.get("dependencies", []):
                name = dep["name"].lower()
                if name in known_issues.get("javascript", {}):
                    for op, vuln_version, cve in known_issues["javascript"][name]:
                        findings.append({
                            "package": dep["name"],
                            "version": dep["version"],
                            "issue": cve,
                            "severity": "high",
                            "language": "javascript",
                        })

        return {
            "success": True,
            "scan_completed": True,
            "findings_count": len(findings),
            "findings": findings,
            "note": "Static pattern matching only. Use dedicated security tools for production.",
        }
