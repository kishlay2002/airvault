"""VaultMind MCP Server

Exposes document intelligence capabilities as MCP tools for integration
with AI agents and LLM clients (e.g., Claude Desktop, Cursor).

Transport: stdio (default) or SSE over HTTP.
"""

import json
import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.mcp.tools import (
    handle_search_documents,
    handle_get_document_source,
    handle_list_collections,
    handle_get_ingestion_status,
    handle_summarize_document,
)

logger = structlog.get_logger()

# MCP Server instance
mcp_server = Server("vaultmind")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Register all VaultMind MCP tools."""
    return [
        Tool(
            name="search_documents",
            description="Search the document knowledge base using natural language. Returns relevant excerpts with citations and source attribution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "collection": {
                        "type": "string",
                        "description": "Collection to search in",
                        "default": "default",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (1-20)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_document_source",
            description="Retrieve the full text of a specific document chunk by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                        "description": "UUID of the chunk to retrieve",
                    },
                },
                "required": ["chunk_id"],
            },
        ),
        Tool(
            name="list_collections",
            description="List all available document collections with their statistics.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_ingestion_status",
            description="Get the current status of the ingestion pipeline including queue depth and recent job statuses.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="summarize_document",
            description="Generate an extractive summary of a specific document by combining its chunks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "UUID of the document to summarize",
                    },
                    "max_chunks": {
                        "type": "integer",
                        "description": "Maximum chunks to include in summary",
                        "default": 10,
                    },
                },
                "required": ["document_id"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route MCP tool calls to their handlers."""
    logger.info("mcp_tool_called", tool=name, arguments=arguments)

    handlers = {
        "search_documents": handle_search_documents,
        "get_document_source": handle_get_document_source,
        "list_collections": handle_list_collections,
        "get_ingestion_status": handle_get_ingestion_status,
        "summarize_document": handle_summarize_document,
    }

    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error("mcp_tool_error", tool=name, error=str(e))
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_mcp_stdio():
    """Run MCP server with stdio transport."""
    logger.info("starting_mcp_server", transport="stdio")
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())
