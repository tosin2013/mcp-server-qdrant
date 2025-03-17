import argparse
import uvicorn

from .sse import create_app


def main():
    """
    Main entry point for the mcp-server-qdrant script defined
    in pyproject.toml. It runs the MCP server with a specific transport
    protocol.
    """

    # Parse the command-line arguments to determine the transport protocol.
    parser = argparse.ArgumentParser(description="mcp-server-qdrant")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        # Run the server with SSE transport
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        # Run the server with stdio transport
        from mcp_server_qdrant.server import mcp
        mcp.run(transport=args.transport)
