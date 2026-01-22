#!/usr/bin/env python3
"""KubeLLM Documentation MCP Server.

Exposes tools for fetching documentation from various sources used by KubeLLM.
"""

import re
from urllib.parse import urlparse
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.types import Resource, ResourceTemplate, Tool, TextContent

from .sources import DOC_SOURCES, get_doc_url, list_sources, list_endpoints

server = Server("kubellm-docs")

# Timeout for HTTP requests
HTTP_TIMEOUT = 30.0

RESOURCE_SCHEME = "kubellm-docs"
RESOURCE_NETLOC = "docs"


def make_doc_uri(source: str, endpoint: str) -> str:
    """Create a stable resource URI for a doc endpoint."""
    return f"{RESOURCE_SCHEME}://{RESOURCE_NETLOC}/{source}/{endpoint}"


def parse_doc_uri(uri: str) -> tuple[str, str] | None:
    """Parse a doc resource URI into (source, endpoint)."""
    parsed = urlparse(uri)
    if parsed.scheme != RESOURCE_SCHEME or parsed.netloc != RESOURCE_NETLOC:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        return None
    source, endpoint = parts[0].lower(), parts[1].lower()
    if source not in DOC_SOURCES or endpoint not in DOC_SOURCES[source]["endpoints"]:
        return None
    return source, endpoint


def html_to_text(html: str) -> str:
    """Convert HTML to plain text, preserving structure."""
    # Remove script and style elements
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert headers
    for i in range(1, 7):
        html = re.sub(rf"<h{i}[^>]*>(.*?)</h{i}>", rf"\n{'#' * i} \1\n", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert code blocks
    html = re.sub(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", r"\n```\n\1\n```\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert lists
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert paragraphs and line breaks
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<div[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</div>", "\n", html, flags=re.IGNORECASE)

    # Convert links
    html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert bold and italic
    html = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove remaining HTML tags
    html = re.sub(r"<[^>]+>", "", html)

    # Decode HTML entities
    html = html.replace("&nbsp;", " ")
    html = html.replace("&lt;", "<")
    html = html.replace("&gt;", ">")
    html = html.replace("&amp;", "&")
    html = html.replace("&quot;", '"')
    html = html.replace("&#39;", "'")

    # Clean up whitespace
    html = re.sub(r"\n{3,}", "\n\n", html)
    html = re.sub(r" {2,}", " ", html)

    return html.strip()


async def fetch_doc(url: str) -> str:
    """Fetch and convert documentation from URL."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=HTTP_TIMEOUT) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; KubeLLM-MCP/1.0; +https://github.com/kubellm)"
        }
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            return html_to_text(response.text)
        elif "text/markdown" in content_type or url.endswith(".md"):
            return response.text
        else:
            return response.text


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available documentation tools."""
    return [
        Tool(
            name="list_doc_sources",
            description="List all available documentation sources (kubernetes, docker, openai, etc.)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="list_doc_endpoints",
            description="List available documentation endpoints for a specific source",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Documentation source ID (e.g., 'kubernetes', 'docker', 'openai')",
                    },
                },
                "required": ["source"],
            },
        ),
        Tool(
            name="fetch_doc",
            description="Fetch documentation from a specific source and endpoint",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Documentation source ID (e.g., 'kubernetes', 'docker', 'openai')",
                    },
                    "endpoint": {
                        "type": "string",
                        "description": "Endpoint within the source (e.g., 'pods', 'probes', 'models')",
                    },
                },
                "required": ["source", "endpoint"],
            },
        ),
        Tool(
            name="fetch_url",
            description="Fetch documentation from any URL directly",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to fetch documentation from",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="search_docs",
            description="Search for a topic across all documentation sources (returns relevant endpoints)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'probes', 'resource limits', 'embeddings')",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all documentation resources."""
    resources: list[Resource] = []
    for source_id, source_info in DOC_SOURCES.items():
        for endpoint in source_info["endpoints"].keys():
            uri = make_doc_uri(source_id, endpoint)
            description = f"{source_info['name']} documentation for '{endpoint}'"
            resources.append(
                Resource(uri=uri, description=description, mimeType="text/plain")
            )
    return resources


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """Expose a template for documentation resources."""
    return [
        ResourceTemplate(
            uriTemplate=f"{RESOURCE_SCHEME}://{RESOURCE_NETLOC}/{{source}}/{{endpoint}}",
            description="Documentation endpoints by source and endpoint ID",
            mimeType="text/plain",
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> list[ReadResourceContents]:
    """Read a documentation resource by URI."""
    parsed = parse_doc_uri(str(uri))
    if parsed is None:
        return [
            ReadResourceContents(
                content=f"Unknown or invalid resource URI: {uri}",
                mime_type="text/plain",
            )
        ]
    source, endpoint = parsed
    url = get_doc_url(source, endpoint)
    content = await fetch_doc(url)
    header = f"# Documentation: {DOC_SOURCES[source]['name']} - {endpoint}\nSource: {url}\n\n"
    return [
        ReadResourceContents(
            content=header + content,
            mime_type="text/plain",
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "list_doc_sources":
            sources = list_sources()
            text = "# Available Documentation Sources\n\n"
            for src in sources:
                text += f"## {src['name']} (`{src['id']}`)\n"
                text += f"Base URL: {src['base_url']}\n"
                text += f"Endpoints: {', '.join(src['endpoints'])}\n\n"
            return [TextContent(type="text", text=text)]

        elif name == "list_doc_endpoints":
            source = arguments.get("source", "").lower()
            endpoints = list_endpoints(source)
            if endpoints is None:
                available = ", ".join(DOC_SOURCES.keys())
                return [TextContent(type="text", text=f"Unknown source: {source}. Available: {available}")]
            src_info = DOC_SOURCES[source]
            text = f"# {src_info['name']} Documentation Endpoints\n\n"
            for ep in endpoints:
                url = get_doc_url(source, ep)
                text += f"- **{ep}**: {url}\n"
            return [TextContent(type="text", text=text)]

        elif name == "fetch_doc":
            source = arguments.get("source", "").lower()
            endpoint = arguments.get("endpoint", "").lower()
            url = get_doc_url(source, endpoint)
            if url is None:
                if source not in DOC_SOURCES:
                    available = ", ".join(DOC_SOURCES.keys())
                    return [TextContent(type="text", text=f"Unknown source: {source}. Available: {available}")]
                else:
                    available = ", ".join(DOC_SOURCES[source]["endpoints"].keys())
                    return [TextContent(type="text", text=f"Unknown endpoint: {endpoint}. Available for {source}: {available}")]
            content = await fetch_doc(url)
            header = f"# Documentation: {DOC_SOURCES[source]['name']} - {endpoint}\nSource: {url}\n\n"
            return [TextContent(type="text", text=header + content)]

        elif name == "fetch_url":
            url = arguments.get("url", "")
            if not url:
                return [TextContent(type="text", text="Error: URL is required")]
            content = await fetch_doc(url)
            header = f"# Documentation from URL\nSource: {url}\n\n"
            return [TextContent(type="text", text=header + content)]

        elif name == "search_docs":
            query = arguments.get("query", "").lower()
            if not query:
                return [TextContent(type="text", text="Error: Query is required")]

            results = []
            for source_id, source_info in DOC_SOURCES.items():
                for endpoint, path in source_info["endpoints"].items():
                    # Match query against source name, endpoint name, or path
                    searchable = f"{source_info['name']} {endpoint} {path}".lower()
                    if query in searchable:
                        url = get_doc_url(source_id, endpoint)
                        results.append({
                            "source": source_id,
                            "source_name": source_info["name"],
                            "endpoint": endpoint,
                            "url": url,
                        })

            if not results:
                text = f"No documentation found matching '{query}'.\n\n"
                text += "Try broader terms or use `list_doc_sources` to see all available sources."
            else:
                text = f"# Documentation matching '{query}'\n\n"
                for r in results:
                    text += f"- **{r['source_name']}** / `{r['endpoint']}`: {r['url']}\n"
                text += f"\nUse `fetch_doc` with source and endpoint to retrieve content."

            return [TextContent(type="text", text=text)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"HTTP Error {e.response.status_code}: {e.response.reason_phrase}")]
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Request Error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
