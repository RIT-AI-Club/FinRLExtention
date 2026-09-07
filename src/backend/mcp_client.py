"""
MCP Client with Gemini API Backend

This module provides an MCP (Model Context Protocol) client that uses
Google's Gemini API (via the google-genai SDK) as the underlying LLM for
processing requests and handling tool calls.
"""
import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Retry policy for Gemini rate limiting (HTTP 429)
_GEMINI_RATE_LIMIT_MAX_RETRIES = 5
_GEMINI_RATE_LIMIT_BASE_DELAY = 2.0  # seconds, doubles each retry


async def _send_message_with_retry(
    chat: "genai.chats.AsyncChat",
    content: Any,
) -> types.GenerateContentResponse:
    """Send a message to Gemini, retrying with exponential backoff on 429s."""
    for attempt in range(_GEMINI_RATE_LIMIT_MAX_RETRIES):
        try:
            return await chat.send_message(content)
        except genai_errors.ClientError as e:
            if e.code != 429 or attempt == _GEMINI_RATE_LIMIT_MAX_RETRIES - 1:
                raise
            wait = _GEMINI_RATE_LIMIT_BASE_DELAY * (2 ** attempt)
            logger.warning(
                f"Gemini rate limit hit (429), retrying in {wait:.0f}s "
                f"(attempt {attempt + 1}/{_GEMINI_RATE_LIMIT_MAX_RETRIES})... {e}"
            )
            await asyncio.sleep(wait)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class GeminiConfig:
    """Configuration for Gemini API."""

    api_key: str
    model: str = "gemini-3.5-flash"
    temperature: float = 0.7
    max_output_tokens: int = 8192


_REPORT_ASSISTANT_SYSTEM_INSTRUCTION = """You are a financial report assistant with access to \
tools for stock research, chart generation, and report formatting.

When the user asks for a report, write-up, or analysis of a stock or company, you MUST use the \
available tools rather than answering from your own knowledge:
1. Call the research tools (e.g. research_stock, research_news, research_topic) to gather \
current data.
2. Call the chart tool (e.g. generate_line_chart) to produce a price chart.
3. Call the report formatting tool (format_report) as the final step, passing it the gathered \
text and chart data — this is what actually produces the polished report and saves it as a \
downloadable PDF.

Never write the report yourself as plain text or markdown — a "report" is only real once \
format_report has produced it. After format_report succeeds, just tell the user their report is \
ready; do not repeat its HTML output back to them.

For questions that are not report requests (e.g. "what tools do you have"), answer directly \
without calling tools."""


class MCPClient:
    """
    MCP Client that connects to MCP servers and uses Gemini API for LLM processing.

    This client manages connections to multiple MCP servers, aggregates their tools,
    and uses Gemini to process user requests while handling tool calls.
    """

    def __init__(self, config_path: Optional[str] = None, mcp_servers_path: Optional[str] = None):
        """
        Initialize the MCP Client.

        Args:
            config_path: Path to the config.yml file. If None, uses default location.
            mcp_servers_path: Path to the mcpservers.yml file. If None, uses default location.
        """
        self.config_path = Path(config_path) if config_path else self._get_default_config_path()
        self.mcp_servers_path = Path(mcp_servers_path) if mcp_servers_path else self._get_default_mcp_servers_path()
        self.config: dict[str, Any] = {}
        self.gemini_config: Optional[GeminiConfig] = None
        self.server_configs: list[MCPServerConfig] = []
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, dict[str, Any]] = {}
        self.tool_to_server: dict[str, str] = {}
        self._client: Optional[genai.Client] = None
        self._exit_stack = AsyncExitStack()

    def _get_default_config_path(self) -> Path:
        """Get the default config path relative to this file."""
        return Path(__file__).parent.parent.parent / "config" / "config.yml"

    def _get_default_mcp_servers_path(self) -> Path:
        """Get the default MCP servers config path relative to this file."""
        return Path(__file__).parent.parent.parent / "config" / "mcpservers.yml"

    def load_config(self) -> None:
        """Load configuration from the YAML config files."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f) or {}

        gemini_cfg = self.config.get("gemini", {})
        api_key = gemini_cfg.get("api_key", "")

        if not api_key:
            raise ValueError("Gemini API key not found in config. Please set 'gemini.api_key' in config.yml")

        self.gemini_config = GeminiConfig(
            api_key=api_key,
            model=gemini_cfg.get("model", "gemini-3.5-flash"),
            temperature=gemini_cfg.get("temperature", 0.7),
            max_output_tokens=gemini_cfg.get("max_output_tokens", 8192),
        )

        self._load_mcp_servers_config()

    def _load_mcp_servers_config(self) -> None:
        """Load MCP servers configuration from the mcpservers.yml file."""
        if not self.mcp_servers_path.exists():
            logger.warning(f"MCP servers config file not found: {self.mcp_servers_path}")
            self.server_configs = []
            return

        with open(self.mcp_servers_path, "r") as f:
            mcp_config = yaml.safe_load(f) or {}

        servers_cfg = mcp_config.get("mcp_servers", [])
        if servers_cfg is not None:
            self.server_configs = [
                MCPServerConfig(
                    name=server.get("name", f"server_{i}"),
                    command=server.get("command", ""),
                    args=server.get("args", []),
                    env=server.get("env", {}),
                )
                for i, server in enumerate(servers_cfg)
            ]

    def _initialize_gemini(self) -> None:
        """Initialize the Gemini API client."""
        if not self.gemini_config:
            raise RuntimeError("Config not loaded. Call load_config() first.")

        self._client = genai.Client(api_key=self.gemini_config.api_key)
        logger.info(f"Initialized Gemini client for model: {self.gemini_config.model}")

    async def connect_to_server(self, server_config: MCPServerConfig) -> ClientSession:
        """
        Connect to an MCP server.

        Args:
            server_config: Configuration for the server to connect to.

        Returns:
            The connected ClientSession.
        """
        merged_env = {**os.environ, **(server_config.env or {})}
        server_params = StdioServerParameters(
            command=server_config.command,
            args=server_config.args,
            env=merged_env,
        )

        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self.sessions[server_config.name] = session
        logger.info(f"Connected to MCP server: {server_config.name}")

        return session

    async def connect_all_servers(self) -> None:
        """Connect to all configured MCP servers."""
        for server_config in self.server_configs:
            if not server_config.command:
                logger.warning(f"Skipping server {server_config.name}: no command specified")
                continue
            for attempt in range(2):
                try:
                    await self.connect_to_server(server_config)
                    break
                except Exception as e:
                    if attempt == 0:
                        logger.warning(f"Retrying server {server_config.name} after error: {e}")
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"Failed to connect to server {server_config.name}: {e}")

    async def discover_tools(self) -> dict[str, dict[str, Any]]:
        """
        Discover all available tools from connected MCP servers.

        Returns:
            Dictionary mapping tool names to their schemas.
        """
        self.tools = {}
        self.tool_to_server = {}

        for server_name, session in self.sessions.items():
            try:
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    tool_name = tool.name
                    self.tools[tool_name] = {
                        "name": tool_name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema,
                    }
                    self.tool_to_server[tool_name] = server_name
                    logger.debug(f"Discovered tool: {tool_name} from {server_name}")
            except Exception as e:
                logger.error(f"Failed to discover tools from {server_name}: {e}")

        logger.info(f"Discovered {len(self.tools)} tools from {len(self.sessions)} servers")
        return self.tools

    def _build_gemini_tools(self) -> list[types.Tool]:
        """
        Convert discovered MCP tools into Gemini tool declarations.

        MCP tool schemas are already standard JSON Schema, so they're passed
        straight through via parameters_json_schema — no manual schema
        translation needed.
        """
        if not self.tools:
            return []

        declarations = [
            types.FunctionDeclaration(
                name=tool_name,
                description=tool_info.get("description", ""),
                parameters_json_schema=tool_info.get("input_schema") or {"type": "object", "properties": {}},
            )
            for tool_name, tool_info in self.tools.items()
        ]
        return [types.Tool(function_declarations=declarations)]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool on the appropriate MCP server.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool (plain Python types).

        Returns:
            The tool's response.
        """
        if tool_name not in self.tool_to_server:
            raise ValueError(f"Unknown tool: {tool_name}")

        server_name = self.tool_to_server[tool_name]
        session = self.sessions.get(server_name)

        if not session:
            raise RuntimeError(f"No session for server: {server_name}")

        logger.debug(f"Calling tool {tool_name} on {server_name} with args: {arguments}")

        result = await session.call_tool(tool_name, arguments)
        return result

    @staticmethod
    def _extract_function_calls(response: types.GenerateContentResponse) -> list[types.FunctionCall]:
        """
        Return the list of function calls from a Gemini response, safely
        handling candidates whose finish_reason is MALFORMED_FUNCTION_CALL.
        """
        try:
            candidate = response.candidates[0]
        except (IndexError, AttributeError, TypeError):
            return []

        if candidate.finish_reason == types.FinishReason.MALFORMED_FUNCTION_CALL:
            logger.warning(
                "Gemini returned MALFORMED_FUNCTION_CALL. "
                "The model could not construct a valid tool call. "
                "Check that the tool schema is correct and all required fields are present."
            )
            return []

        return response.function_calls or []

    async def process_message(
        self,
        message: str,
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        """
        Process a user message using Gemini and available MCP tools.

        Args:
            message: The user's message.
            conversation_history: Optional list of previous messages for context.

        Returns:
            The assistant's response.
        """
        if not self._client:
            self._initialize_gemini()

        history = conversation_history or []

        chat = self._client.aio.chats.create(
            model=self.gemini_config.model,
            config=types.GenerateContentConfig(
                system_instruction=_REPORT_ASSISTANT_SYSTEM_INSTRUCTION,
                temperature=self.gemini_config.temperature,
                max_output_tokens=self.gemini_config.max_output_tokens,
                tools=self._build_gemini_tools() or None,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
            history=self._convert_history_to_gemini(history),
        )

        # ------------------------------------------------------------------ #
        # Initial send                                                         #
        # ------------------------------------------------------------------ #
        try:
            response = await _send_message_with_retry(chat, message)
        except Exception as e:
            logger.error(f"Gemini send_message failed: {e}")
            raise

        # ------------------------------------------------------------------ #
        # Agentic tool-call loop                                               #
        # ------------------------------------------------------------------ #
        max_iterations = 10  # safety guard against infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            function_calls = self._extract_function_calls(response)
            if not function_calls:
                break

            function_response_parts: list[types.Part] = []

            for fc in function_calls:
                tool_name = fc.name
                arguments: dict[str, Any] = fc.args or {}

                logger.debug(f"Tool call: {tool_name}({json.dumps(arguments, default=str)})")

                try:
                    result = await self.call_tool(tool_name, arguments)

                    content = result.content if hasattr(result, "content") else str(result)
                    if hasattr(content, "__iter__") and not isinstance(content, str):
                        content = "\n".join(
                            item.text if hasattr(item, "text") else str(item)
                            for item in content
                        )

                    function_response_parts.append(
                        types.Part.from_function_response(name=tool_name, response={"result": content})
                    )

                except Exception as e:
                    logger.error(f"Tool call failed for {tool_name}: {e}")
                    function_response_parts.append(
                        types.Part.from_function_response(name=tool_name, response={"error": str(e)})
                    )

            # Send all tool results back in one turn
            try:
                response = await _send_message_with_retry(chat, function_response_parts)
            except Exception as e:
                logger.error(f"Gemini send_message (tool response) failed: {e}")
                raise

        # ------------------------------------------------------------------ #
        # Extract final text                                                   #
        # ------------------------------------------------------------------ #
        response_text = response.text or ""

        if not response_text:
            logger.warning("No text content in final Gemini response.")

        return response_text

    def _convert_history_to_gemini(self, history: list[dict[str, Any]]) -> list[types.Content]:
        """Convert conversation history (role/content dicts) to Gemini Content objects."""
        return [
            types.Content(
                role="user" if msg.get("role", "user") == "user" else "model",
                parts=[types.Part.from_text(text=msg.get("content", ""))],
            )
            for msg in history
        ]

    async def close(self) -> None:
        """Close all server connections."""
        await self._exit_stack.aclose()
        self.sessions.clear()
        self.tools.clear()
        self.tool_to_server.clear()


# --------------------------------------------------------------------------- #
# Factory                                                                      #
# --------------------------------------------------------------------------- #

async def create_mcp_client(
    config_path: Optional[str] = None,
    mcp_servers_path: Optional[str] = None,
) -> MCPClient:
    """
    Create and initialize an MCP client.

    Args:
        config_path: Optional path to config file.
        mcp_servers_path: Optional path to MCP servers config file.

    Returns:
        Initialized MCPClient instance.
    """
    client = MCPClient(config_path, mcp_servers_path)
    client.load_config()
    await client.connect_all_servers()
    await client.discover_tools()
    return client


async def main():
    """Example usage of the MCP client."""
    logging.basicConfig(level=logging.INFO)

    client = await create_mcp_client()

    try:
        print("Available tools:", list(client.tools.keys()))

        response = await client.process_message(
            "Hello! What tools do you have available? Do not call any tools"
        )
        print("Response:", response)

        while (inp := input(">> ")) != "bye":
            response = await client.process_message(inp)
            print(">", response)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
