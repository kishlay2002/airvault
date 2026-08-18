"""CLI entry point: `airvault serve` for REST or MCP mode."""

import sys


def main():
    """Route CLI commands."""
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        _serve()
    else:
        print("Usage:")
        print("  airvault serve              # Start REST API server")
        print("  airvault serve --mode mcp   # Start MCP server (stdio)")
        print("  airvault serve --port 8000  # Custom port")
        sys.exit(1)


def _serve():
    import argparse

    parser = argparse.ArgumentParser(description="AirVault Server")
    parser.add_argument("--mode", choices=["rest", "mcp"], default="rest")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)

    # Skip 'serve' from argv
    args = parser.parse_args(sys.argv[2:])

    if args.mode == "mcp":
        print("Starting AirVault MCP server (stdio)...")
        import asyncio
        from airvault.config import AirVaultConfig
        # MCP server import is deferred to avoid hard dependency
        try:
            from airvault._mcp_server import run_mcp
            asyncio.run(run_mcp(AirVaultConfig()))
        except ImportError:
            print("MCP support not installed. Run: pip install airvault[mcp]")
            sys.exit(1)
    else:
        print(f"Starting AirVault REST API on {args.host}:{args.port}...")
        try:
            import uvicorn
            uvicorn.run(
                "airvault._rest_server:app",
                host=args.host,
                port=args.port,
            )
        except ImportError:
            print("Server dependencies not installed. Run: pip install airvault[server]")
            sys.exit(1)


if __name__ == "__main__":
    main()
