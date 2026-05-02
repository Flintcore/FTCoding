"""Self-iteration script - run daily via cron or scheduler."""
import asyncio
import sys
from pathlib import Path

from ftcoding.kernel.kernel import Kernel
from ftcoding.kernel.config import load_config
from ftcoding.kernel.cron_engine import CronEngine
from ftcoding.plugins.code_insight.plugin import CodeInsightPlugin
from ftcoding.plugins.code_editor.plugin import CodeEditorPlugin
from ftcoding.plugins.execution_env.plugin import ExecutionEnvPlugin
from ftcoding.plugins.git_workflow.plugin import GitWorkflowPlugin
from ftcoding.plugins.code_generator.plugin import CodeGeneratorPlugin
from ftcoding.plugins.project_scaffold.plugin import ProjectScaffoldPlugin


async def main():
    """Run self-iteration tasks."""
    print("=" * 50)
    print("FTcoding Self-Iteration Engine")
    print("=" * 50)

    config = load_config()
    kernel = Kernel(config)

    try:
        await kernel.initialize()

        kernel.plugin_manager.register(CodeInsightPlugin())
        kernel.plugin_manager.register(CodeEditorPlugin())
        kernel.plugin_manager.register(ExecutionEnvPlugin())
        kernel.plugin_manager.register(GitWorkflowPlugin())
        kernel.plugin_manager.register(CodeGeneratorPlugin())
        kernel.plugin_manager.register(ProjectScaffoldPlugin())
        await kernel.plugin_manager.initialize_all()

        cron = CronEngine(kernel)

        task = sys.argv[1] if len(sys.argv) > 1 else "all"

        if task in ("all", "health"):
            await cron._health_check()
        if task in ("all", "ideate"):
            await cron._ideate_feature()
        if task in ("all", "deps"):
            await cron._dependency_check()

        print("\nSelf-iteration complete!")

    finally:
        await kernel.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
