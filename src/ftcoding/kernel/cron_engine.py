"""Self-iteration engine - daily health checks and feature ideation."""
from __future__ import annotations
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ftcoding.kernel.kernel import Kernel


class CronEngine:
    """Daily self-iteration scheduler for FTcoding."""

    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.scheduler = AsyncIOScheduler()
        self._running = False

    def setup(self) -> None:
        """Setup scheduled tasks."""
        config = self.kernel.config

        if not config.cron_enabled:
            return

        self.scheduler.add_job(
            self._health_check,
            trigger=CronTrigger(hour=config.cron_hour, minute=config.cron_minute),
            id="health_check",
            name="Daily Health Check"
        )

        self.scheduler.add_job(
            self._ideate_feature,
            trigger=CronTrigger(hour=config.cron_hour, minute=config.cron_minute + 5),
            id="ideate_feature",
            name="Daily Feature Ideation"
        )

        self.scheduler.add_job(
            self._dependency_check,
            trigger=CronTrigger(day_of_week="sun", hour=10, minute=0),
            id="dependency_check",
            name="Weekly Dependency Check"
        )

    async def start(self) -> None:
        """Start the scheduler."""
        self.setup()
        self.scheduler.start()
        self._running = True

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False

    async def _health_check(self) -> None:
        """Run daily health check."""
        print(f"[{datetime.now()}] Running daily health check...")

        health = self.kernel.health()
        status_file = ".ftcoding/health.log"

        with open(status_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()}: {health}\n")

        for name, status in health.get("plugins", {}).items():
            if status.get("status") != "healthy":
                print(f"  Warning: Plugin '{name}' is {status.get('status')}")

        print(f"[{datetime.now()}] Health check complete")

    async def _ideate_feature(self) -> None:
        """Generate new feature ideas based on project patterns."""
        print(f"[{datetime.now()}] Generating feature ideas...")

        patterns = self.kernel.memory.get_patterns("project_structure")
        suggestions = []

        if patterns:
            all_patterns = " ".join([p["pattern"] for p in patterns])

            if "node_modules" in all_patterns or "package.json" in all_patterns:
                suggestions.append("Add npm/yarn workflow plugin")
            if "requirements.txt" in all_patterns or "pyproject.toml" in all_patterns:
                suggestions.append("Add pip/poetry workflow plugin")
            if ".github" in all_patterns:
                suggestions.append("Add CI/CD pipeline analysis plugin")
            if "docker" in all_patterns or "Dockerfile" in all_patterns:
                suggestions.append("Add Docker management plugin")

        if suggestions:
            self.kernel.memory.set_knowledge("pending_suggestions", suggestions)
            print(f"  New suggestions: {suggestions}")
        else:
            print(f"  No new suggestions today")

        print(f"[{datetime.now()}] Feature ideation complete")

    async def _dependency_check(self) -> None:
        """Check for dependency updates."""
        print(f"[{datetime.now()}] Checking dependencies...")
        import subprocess
        try:
            result = subprocess.run(
                ["pip", "list", "--outdated"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.stdout:
                print(f"  Outdated packages found")
                with open(".ftcoding/outdated.log", "w") as f:
                    f.write(result.stdout)
            else:
                print(f"  All dependencies up to date")
        except Exception as e:
            print(f"  Could not check dependencies: {e}")

    def run_now(self, task: str) -> None:
        """Run a specific task immediately."""
        tasks = {
            "health": self._health_check,
            "ideate": self._ideate_feature,
            "deps": self._dependency_check,
        }
        if task in tasks:
            asyncio.create_task(tasks[task]())
