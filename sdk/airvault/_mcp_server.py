"""MCP server wrapping the AirVault SDK.

Exposes AirVault as MCP tools for AI agent integration.
Thin wrapper — all logic lives in airvault.engine.AirVault.
"""

from __future__ import annotations

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from airvault import AirVault, AirVaultConfig

TOOLS = [
    Tool(
        name="search_documents",
        description="Search the document knowledge base using natural language. Returns relevant excerpts with citations.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "collection": {"type": "string", "description": "Collection to search", "default": "default"},
                "clearance": {"type": "string", "description": "User clearance level", "default": "public"},
                "top_k": {"type": "integer", "description": "Number of results", "default": 5},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="list_collections",
        description="List all available document collections with statistics.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_ingestion_status",
        description="Get health status of the AirVault engine and all dependencies.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ingest_text",
        description="Ingest raw text into the knowledge base.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to ingest"},
                "source_name": {"type": "string", "description": "Source name", "default": "mcp_input"},
                "collection": {"type": "string", "default": "default"},
            },
            "required": ["text"],
        },
    ),
]


async def run_mcp(config: AirVaultConfig) -> None:
    """Run AirVault as an MCP server over stdio."""
    engine = AirVault(config)
    server = Server("airvault")

    @server.list_tools()
    async def list_tools():
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "search_documents":
            result = await engine.query(
                text=arguments["query"],
                collection=arguments.get("collection", "default"),
                clearance=arguments.get("clearance", "public"),
                top_k=arguments.get("top_k", 5),
            )
            output = f"Answer: {result.answer}\n\n"
            for c in result.citations:
                output += f"- [{c.source}:{c.page}] (score={c.score}) {c.excerpt[:200]}\n"
            output += f"\nRetrieved: {result.chunks_retrieved}, Redacted: {result.chunks_redacted}"
            return [TextContent(type="text", text=output)]

        elif name == "list_collections":
            cols = await engine.list_collections()
            lines = [f"- {c.name}: {c.document_count} docs, {c.chunk_count} chunks" for c in cols]
            return [TextContent(type="text", text="\n".join(lines) or "No collections.")]

        elif name == "get_ingestion_status":
            health = await engine.health()
            lines = [f"Status: {health.status}"]
            for k, v in health.checks.items():
                lines.append(f"  {k}: {v}")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "ingest_text":
            result = await engine.ingest_text(
                text=arguments["text"],
                source_name=arguments.get("source_name", "mcp_input"),
                collection=arguments.get("collection", "default"),
            )
            return [TextContent(
                type="text",
                text=f"Ingested: {result.filename}, {result.chunk_count} chunks, sensitivity={result.sensitivity.value}",
            )]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
