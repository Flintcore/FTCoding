"""FastAPI server for IDE integration via HTTP/WebSocket."""
from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ftcoding.kernel.kernel import Kernel
from ftcoding.kernel.config import Config, load_config
from ftcoding.plugins.code_insight.plugin import CodeInsightPlugin
from ftcoding.plugins.code_editor.plugin import CodeEditorPlugin
from ftcoding.plugins.execution_env.plugin import ExecutionEnvPlugin
from ftcoding.plugins.git_workflow.plugin import GitWorkflowPlugin


kernel: Kernel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage kernel lifecycle."""
    global kernel
    config = load_config()
    kernel = Kernel(config)
    await kernel.initialize()

    kernel.plugin_manager.register(CodeInsightPlugin())
    kernel.plugin_manager.register(CodeEditorPlugin())
    kernel.plugin_manager.register(ExecutionEnvPlugin())
    kernel.plugin_manager.register(GitWorkflowPlugin())
    await kernel.plugin_manager.initialize_all()

    yield

    await kernel.shutdown()


app = FastAPI(
    title="FTcoding IDE Bridge",
    description="HTTP/WebSocket bridge for IDE integration",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    if kernel:
        return kernel.health()
    return {"status": "not_initialized"}


@app.get("/plugins")
async def list_plugins():
    """List available plugins."""
    if kernel:
        return {"plugins": kernel.plugin_manager.list_plugins()}
    return {"plugins": []}


@app.post("/command/{plugin_name}/{command}")
async def send_command(plugin_name: str, command: str, payload: dict):
    """Send command to a plugin."""
    if not kernel:
        return {"error": "Kernel not initialized"}
    return await kernel.send_command(plugin_name, command, payload)


@app.post("/index")
async def index_project(path: str | None = None):
    """Index a project for code understanding."""
    if not kernel:
        return {"error": "Kernel not initialized"}
    target = path or str(kernel.config.project_root)
    return await kernel.send_command("code_insight", "index_project", {"path": target})


@app.post("/search")
async def search_code(query: str):
    """Search code in indexed project."""
    if not kernel:
        return {"error": "Kernel not initialized"}
    return await kernel.send_command("code_insight", "search_code", {"query": query})


@app.get("/file/{file_path:path}")
async def read_file(file_path: str):
    """Read a file's content."""
    if not kernel:
        return {"error": "Kernel not initialized"}
    return await kernel.send_command("code_editor", "read_file", {"path": file_path})


@app.post("/file/{file_path:path}")
async def write_file(file_path: str, content: str):
    """Write content to a file."""
    if not kernel:
        return {"error": "Kernel not initialized"}
    return await kernel.send_command("code_editor", "write_file", {
        "path": file_path,
        "content": content
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time communication."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command", "")
            plugin = data.get("plugin", "")
            payload = data.get("payload", {})

            if kernel and plugin and command:
                result = await kernel.send_command(plugin, command, payload)
                await websocket.send_json(result)
            else:
                await websocket.send_json({"error": "Invalid request"})

    except WebSocketDisconnect:
        pass


def start_server(host: str = "127.0.0.1", port: int = 8787):
    """Start the IDE bridge server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
