import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any
import datetime

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp.server.sse import SseServerTransport
from mcp.server.lowlevel import Server

from .utils.logger import get_logger

logger = get_logger(__name__)

async def sse_endpoint(request: Request):
    """SSE endpoint for MCP server."""
    logger.info("[SSE] => sse_endpoint called")

    # SSE transport from the MCP SDK
    sse_transport = SseServerTransport("/sse/messages")
    scope = request.scope
    receive = request.receive
    send = request._send

    async with sse_transport.connect_sse(scope, receive, send) as (read_st, write_st):
        logger.info("[SSE] run mcp_server with SSE transport => calling 'mcp_server.run'")
        init_opts = request.app.state.mcp_server.create_initialization_options()
        # Run the server with read/write streams
        await request.app.state.mcp_server.run(read_st, write_st, init_opts)

    logger.info("[SSE] => SSE session ended")
    return

async def post_handler(request: Request):
    """Handle POST requests to /sse/messages."""
    raw = await request.body()
    body_str = raw.decode("utf-8")
    logger.info(f"[POST /sse/messages] => {body_str}")

    if not body_str.strip():
        return JSONResponse({"error": "Empty body"}, status_code=400)

    try:
        msg = await request.json()
    except Exception as e:
        logger.error(f"[POST] JSON parse error: {e}")
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    if msg.get("jsonrpc") != "2.0":
        logger.error("[POST] => Missing jsonrpc=2.0")
        return JSONResponse({"error": "Missing jsonrpc=2.0"}, status_code=400)

    id_ = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params", {})

    logger.debug(f"[POST] method={method}, id={id_}, params={params}")

    # If no id => it's a notification
    if id_ is None:
        logger.info(f"Received NOTIFICATION => method={method}, params={params}")
        return JSONResponse({}, status_code=200)

    # Handle the request
    try:
        result = await request.app.state.mcp_server.handle_request(msg)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": id_,
                "error": {"code": -32603, "message": str(e)},
            },
            status_code=500,
        )

async def health_endpoint(request: Request):
    """Health check endpoint for the server."""
    logger.info("[HEALTH] => health endpoint called")
    
    # Simple health check that doesn't depend on the MCP server being fully initialized
    health_status = {
        "status": "healthy",
        "timestamp": str(datetime.datetime.utcnow()),
        "service": "mcp-server-qdrant"
    }
    
    # If the MCP server is initialized, include more detailed health information
    if hasattr(request.app.state, "mcp_server") and request.app.state.mcp_server is not None:
        try:
            # Add more detailed health information if available
            health_status["server_initialized"] = True
        except Exception as e:
            logger.warning(f"Error getting detailed health status: {e}")
            health_status["server_initialized"] = False
    else:
        health_status["server_initialized"] = False
        
    return JSONResponse(health_status, status_code=200)

@asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[Dict[str, Any]]:
    """Lifespan context manager for the Starlette application."""
    from .server import mcp
    app.state.mcp_server = mcp
    yield
    app.state.mcp_server = None

def create_app() -> Starlette:
    """Create and configure the Starlette application."""
    routes = [
        Route("/sse", endpoint=sse_endpoint, methods=["GET"]),
        Route("/sse/messages", endpoint=post_handler, methods=["POST"]),
        Route("/health", endpoint=health_endpoint, methods=["GET"]),
    ]
    return Starlette(debug=True, routes=routes, lifespan=lifespan) 