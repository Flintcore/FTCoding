"""Interactive CLI for FTcoding."""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from ftcoding.kernel.kernel import Kernel
from ftcoding.kernel.config import Config, load_config


console = Console()


@click.group(invoke_without_command=True)
@click.option("--project", "-p", type=click.Path(), help="Project root directory")
@click.option("--config", "config_path", type=click.Path(), help="Config file path")
@click.pass_context
def main(ctx, project, config_path):
    """FTcoding - 中国开发者的本地Coding Agent

    数据不出网，越用越懂你的项目
    """
    if ctx.invoked_subcommand is None:
        asyncio.run(interactive_mode(project, config_path))


async def interactive_mode(project_root: str | None, config_path: str | None):
    """Run interactive CLI session."""
    console.print(Panel.fit(
        "[bold cyan]FTcoding[/bold cyan] - 中国开发者的本地Coding Agent\n"
        "[dim]数据不出网，越用越懂你的项目[/dim]\n"
        "[dim]输入 /help 查看命令[/dim]",
        title="v0.1.0",
        border_style="cyan"
    ))

    config = load_config(Path(config_path) if config_path else None)
    if project_root:
        config.project_root = Path(project_root)

    kernel = Kernel(config)

    try:
        await kernel.initialize()
        console.print("[green]Kernel initialized successfully[/green]")

        from ftcoding.plugins.code_insight.plugin import CodeInsightPlugin
        from ftcoding.plugins.code_editor.plugin import CodeEditorPlugin
        from ftcoding.plugins.execution_env.plugin import ExecutionEnvPlugin
        from ftcoding.plugins.git_workflow.plugin import GitWorkflowPlugin

        kernel.plugin_manager.register(CodeInsightPlugin())
        kernel.plugin_manager.register(CodeEditorPlugin())
        kernel.plugin_manager.register(ExecutionEnvPlugin())
        kernel.plugin_manager.register(GitWorkflowPlugin())
        await kernel.plugin_manager.initialize_all()

        console.print(f"[green]Plugins loaded: {kernel.plugin_manager.list_plugins()}[/green]\n")

        while True:
            try:
                user_input = Prompt.ask("[cyan]ftcoding[/cyan]")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input in ["/exit", "/quit", "exit", "quit"]:
                    break

                if user_input == "/help":
                    show_help()
                    continue

                if user_input == "/health":
                    show_health(kernel)
                    continue

                if user_input.startswith("/index"):
                    await handle_index(kernel, user_input)
                    continue

                if user_input.startswith("/search"):
                    await handle_search(kernel, user_input)
                    continue

                if user_input.startswith("/read"):
                    await handle_read(kernel, user_input)
                    continue

                if user_input.startswith("/edit"):
                    await handle_edit(kernel, user_input)
                    continue

                if user_input.startswith("/run"):
                    await handle_run(kernel, user_input)
                    continue

                if user_input.startswith("/test"):
                    await handle_test(kernel, user_input)
                    continue

                if user_input.startswith("/git"):
                    await handle_git(kernel, user_input)
                    continue

                await handle_query(kernel, user_input)

            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    finally:
        await kernel.shutdown()
        console.print("\n[dim]Goodbye![/dim]")


def show_help():
    """Display help information."""
    table = Table(title="FTcoding Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("/help", "Show this help"),
        ("/health", "Check system health"),
        ("/index [path]", "Index project for code understanding"),
        ("/search <query>", "Search code in project"),
        ("/read <file>", "Read file content"),
        ("/edit <file>", "Edit a file (interactive)"),
        ("/run <command>", "Run a command safely"),
        ("/test [path]", "Run tests"),
        ("/git status", "Show git status"),
        ("/git diff", "Show git diff"),
        ("/git log [n]", "Show git log (last n commits)"),
        ("/git commit <msg>", "Commit changes"),
        ("/git branch", "List branches"),
        ("/exit", "Exit FTcoding"),
        ("<natural language>", "Ask FTcoding anything"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


def show_health(kernel: Kernel):
    """Display system health."""
    health = kernel.health()
    table = Table(title="System Health")
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    for name, status in health.items():
        if isinstance(status, dict):
            stat = status.get("status", "unknown")
            color = "green" if stat == "healthy" else "red"
            table.add_row(name, f"[{color}]{stat}[/{color}]")
        else:
            table.add_row(name, str(status))

    console.print(table)


async def handle_index(kernel: Kernel, cmd: str):
    """Handle /index command."""
    parts = cmd.split(maxsplit=1)
    path = parts[1] if len(parts) > 1 else str(kernel.config.project_root)

    with console.status("[yellow]Indexing project...[/yellow]"):
        result = await kernel.send_command("code_insight", "index_project", {"path": path})

    if result.get("success"):
        console.print(f"[green]Indexed {result['files_indexed']} files[/green]")
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")


async def handle_search(kernel: Kernel, cmd: str):
    """Handle /search command."""
    parts = cmd.split(maxsplit=1)
    if len(parts) < 2:
        console.print("[red]Usage: /search <query>[/red]")
        return

    query = parts[1]
    with console.status(f"[yellow]Searching for '{query}'...[/yellow]"):
        result = await kernel.send_command("code_insight", "search_code", {"query": query})

    if result.get("success"):
        results = result.get("results", [])
        if not results:
            console.print("[dim]No results found[/dim]")
            return

        table = Table(title=f"Search Results for '{query}'")
        table.add_column("File", style="cyan")
        table.add_column("Symbols")
        table.add_column("Preview", max_width=50)

        for r in results:
            table.add_row(
                r["file"],
                ", ".join(r.get("symbols", [])),
                r.get("preview", "")[:100]
            )
        console.print(table)
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")


async def handle_read(kernel: Kernel, cmd: str):
    """Handle /read command."""
    parts = cmd.split(maxsplit=1)
    if len(parts) < 2:
        console.print("[red]Usage: /read <file>[/red]")
        return

    file_path = parts[1]
    result = await kernel.send_command("code_editor", "read_file", {"path": file_path})

    if result.get("success"):
        content = result["content"]
        ext = Path(file_path).suffix
        lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript",
                    ".go": "go", ".rs": "rust", ".java": "java"}
        lang = lang_map.get(ext, "text")

        syntax = Syntax(content, lang, line_numbers=True)
        console.print(Panel(syntax, title=file_path))
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")


async def handle_edit(kernel: Kernel, cmd: str):
    """Handle /edit command."""
    parts = cmd.split(maxsplit=1)
    if len(parts) < 2:
        console.print("[red]Usage: /edit <file>[/red]")
        return

    file_path = parts[1]
    result = await kernel.send_command("code_editor", "read_file", {"path": file_path})

    if result.get("success"):
        console.print(f"[yellow]File: {file_path}[/yellow]")
        console.print("Use /write <file> to overwrite with new content")
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")


async def handle_run(kernel: Kernel, cmd: str):
    """Handle /run command."""
    parts = cmd.split(maxsplit=1)
    if len(parts) < 2:
        console.print("[red]Usage: /run <command>[/red]")
        return

    command = parts[1]
    with console.status(f"[yellow]Running: {command}[/yellow]"):
        result = await kernel.send_command("execution_env", "execute", {"command": command})

    if result.get("success"):
        if result.get("stdout"):
            console.print(result["stdout"])
        if result.get("stderr"):
            console.print(f"[yellow]{result['stderr']}[/yellow]")
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")
        if result.get("stderr"):
            console.print(f"[yellow]{result['stderr']}[/yellow]")


async def handle_test(kernel: Kernel, cmd: str):
    """Handle /test command."""
    parts = cmd.split()
    path = parts[1] if len(parts) > 1 else "."

    with console.status("[yellow]Running tests...[/yellow]"):
        result = await kernel.send_command("execution_env", "run_tests", {"path": path})

    if result.get("success"):
        console.print("[green]Tests passed![/green]")
        if result.get("stdout"):
            console.print(result["stdout"])
    else:
        console.print("[red]Tests failed or error[/red]")
        if result.get("stdout"):
            console.print(result["stdout"])
        if result.get("stderr"):
            console.print(f"[yellow]{result['stderr']}[/yellow]")


async def handle_git(kernel: Kernel, cmd: str):
    """Handle /git command."""
    parts = cmd.split(maxsplit=2)
    if len(parts) < 2:
        console.print("[red]Usage: /git status|diff|log|commit <msg>|branch[/red]")
        return

    subcmd = parts[1].lower()

    if subcmd == "status":
        result = await kernel.send_command("git_workflow", "status", {})
        if result.get("success"):
            console.print(f"[cyan]Branch:[/cyan] {result.get('branch', 'unknown')}")
            files = result.get("files", {})
            for status, items in files.items():
                if items:
                    console.print(f"[yellow]{status}:[/yellow] {', '.join(items)}")
        else:
            console.print(f"[red]Error: {result.get('error')}[/red]")

    elif subcmd == "diff":
        with console.status("[yellow]Getting diff...[/yellow]"):
            result = await kernel.send_command("git_workflow", "diff", {})
        if result.get("success"):
            if result.get("diff"):
                console.print(result["diff"])
            else:
                console.print("[dim]No changes[/dim]")
        else:
            console.print(f"[red]Error: {result.get('error')}[/red]")

    elif subcmd == "log":
        limit = int(parts[2]) if len(parts) > 2 else 10
        result = await kernel.send_command("git_workflow", "log", {"limit": limit})
        if result.get("success"):
            table = Table(title=f"Git Log (last {limit})")
            table.add_column("Hash", style="cyan")
            table.add_column("Date")
            table.add_column("Author")
            table.add_column("Message")
            for c in result.get("commits", []):
                table.add_row(c["hash"], c["date"], c["author"], c["message"])
            console.print(table)
        else:
            console.print(f"[red]Error: {result.get('error')}[/red]")

    elif subcmd == "commit":
        if len(parts) < 3:
            console.print("[red]Usage: /git commit <message>[/red]")
            return
        message = parts[2]
        with console.status("[yellow]Committing...[/yellow]"):
            result = await kernel.send_command("git_workflow", "commit", {
                "message": message,
                "all": True
            })
        if result.get("success"):
            console.print(f"[green]Committed: {message}[/green]")
        else:
            console.print(f"[red]Error: {result.get('error')}[/red]")

    elif subcmd == "branch":
        result = await kernel.send_command("git_workflow", "branch_list", {})
        if result.get("success"):
            for b in result.get("branches", []):
                marker = "* " if b["current"] else "  "
                console.print(f"{marker}[cyan]{b['name']}[/cyan]")
        else:
            console.print(f"[red]Error: {result.get('error')}[/red]")

    else:
        console.print(f"[red]Unknown git command: {subcmd}[/red]")


async def handle_query(kernel: Kernel, query: str):
    """Handle natural language query."""
    console.print(f"[dim]Processing: {query}[/dim]")

    search_result = await kernel.send_command("code_insight", "search_code", {"query": query})

    if search_result.get("success") and search_result.get("results"):
        results = search_result["results"]
        console.print(f"[green]Found {len(results)} relevant files:[/green]")
        for r in results[:3]:
            console.print(f"  [cyan]{r['file']}[/cyan]")
    else:
        console.print("[dim]No relevant code found. Try /index first.[/dim]")


if __name__ == "__main__":
    main()
