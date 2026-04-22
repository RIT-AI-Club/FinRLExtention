"""
MCP Client with Gemini API Backend

This module provides an MCP (Model Context Protocol) client that uses
Google's Gemini API as the underlying LLM for processing requests and
handling tool calls.
"""
import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import google.generativeai as genai
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Gemini finish_reason codes
_FINISH_REASON_MALFORMED_FUNCTION_CALL = 12
_FINISH_REASON_STOP = 1


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
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_output_tokens: int = 8192


def _fc_args_to_python(fc: Any) -> dict[str, Any]:
    """
    Extract function-call arguments from a Gemini FunctionCall object as a
    plain Python dict, bypassing proto-plus wrapper types entirely.

    The most reliable path is fc._pb.args (a raw google.protobuf.Struct),
    which MessageToDict converts perfectly — including nested lists/numbers.
    Multiple fallbacks handle edge cases.
    """
    if fc is None:
        return {}

    # Primary: raw protobuf Struct via fc._pb.args
    try:
        from google.protobuf.json_format import MessageToDict
        result = MessageToDict(fc._pb.args, preserving_proto_field_name=True)
        logger.debug(f"fc_args converted via _pb.args: {result}")
        return result
    except Exception as e:
        logger.debug(f"_pb.args MessageToDict failed ({e}), trying manual walk")

    # Fallback A: manual walk of fc._pb.args Struct fields
    try:
        return _struct_to_python(fc._pb.args)
    except Exception as e:
        logger.debug(f"Manual struct walk failed ({e}), trying proto-plus iteration")

    # Fallback B: proto-plus MapComposite iteration
    try:
        return {k: _value_to_python(v) for k, v in (fc.args or {}).items()}
    except Exception as e:
        logger.warning(f"All fc.args conversion paths failed: {e}. Returning empty dict.")
        return {}


def _struct_to_python(struct: Any) -> dict:
    """Convert a google.protobuf.Struct to a plain Python dict."""
    return {k: _value_to_python(v) for k, v in struct.fields.items()}


def _value_to_python(value: Any) -> Any:
    """
    Convert a google.protobuf.Value (oneof) or any proto-plus wrapper
    to its Python equivalent.
    """
    # google.protobuf.Value (oneof) — most common case for fc._pb.args values
    try:
        from google.protobuf import struct_pb2
        if isinstance(value, struct_pb2.Value):
            kind = value.WhichOneof("kind")
            if kind == "null_value":
                return None
            if kind == "bool_value":
                return bool(value.bool_value)
            if kind == "number_value":
                v = value.number_value
                return int(v) if v == int(v) else v
            if kind == "string_value":
                return value.string_value
            if kind == "list_value":
                return [_value_to_python(i) for i in value.list_value.values]
            if kind == "struct_value":
                return _struct_to_python(value.struct_value)
            return None
        if isinstance(value, struct_pb2.ListValue):
            return [_value_to_python(i) for i in value.values]
        if isinstance(value, struct_pb2.Struct):
            return _struct_to_python(value)
    except ImportError:
        pass

    # proto-plus RepeatedComposite / RepeatedScalar
    try:
        from proto.marshal.collections.repeated import RepeatedComposite, RepeatedScalar
        if isinstance(value, (RepeatedComposite, RepeatedScalar)):
            return [_value_to_python(i) for i in value]
    except ImportError:
        pass

    # proto-plus MapComposite
    try:
        from proto.marshal.collections.maps import MapComposite
        if isinstance(value, MapComposite):
            return {k: _value_to_python(v) for k, v in value.items()}
    except ImportError:
        pass

    # Any other protobuf Message
    try:
        from google.protobuf.message import Message as PbMessage
        from google.protobuf.json_format import MessageToDict
        if isinstance(value, PbMessage):
            return MessageToDict(value, preserving_proto_field_name=True)
    except ImportError:
        pass

    # Plain Python containers
    if isinstance(value, dict):
        return {k: _value_to_python(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_value_to_python(i) for i in value]

    # Primitive scalar
    return value


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
        self._model: Optional[genai.GenerativeModel] = None
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
            model=gemini_cfg.get("model", "gemini-2.5-flash"),
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

        genai.configure(api_key=self.gemini_config.api_key)

        self._model = genai.GenerativeModel(
            model_name=self.gemini_config.model,
            generation_config=genai.GenerationConfig(
                temperature=self.gemini_config.temperature,
                max_output_tokens=self.gemini_config.max_output_tokens,
            ),
        )

        logger.info(f"Initialized Gemini model: {self.gemini_config.model}")

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

    # Fields supported by Gemini's Schema proto
    _GEMINI_SCHEMA_FIELDS = {
        "type", "format", "description", "nullable",
        "enum", "items", "properties", "required",
    }

    def _sanitize_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Strip fields unsupported by Gemini, ensure arrays always have an
        'items' sub-schema, and recurse into nested properties.
        """
        schema = {k: v for k, v in schema.items() if k in self._GEMINI_SCHEMA_FIELDS}

        # Arrays must have an items definition
        if schema.get("type") == "array" and "items" not in schema:
            schema["items"] = {"type": "string"}

        if "items" in schema:
            schema["items"] = self._sanitize_schema(schema["items"])

        if "properties" in schema:
            schema["properties"] = {
                k: self._sanitize_schema(v)
                for k, v in schema["properties"].items()
            }

        return schema

    def _convert_tools_to_gemini_format(self) -> list[dict[str, Any]]:
        """Convert MCP tools to Gemini function declarations format."""
        gemini_tools = []

        for tool_name, tool_info in self.tools.items():
            input_schema = tool_info.get("input_schema", {})

            properties = {
                k: self._sanitize_schema(v)
                for k, v in input_schema.get("properties", {}).items()
            }
            required = input_schema.get("required", [])

            parameters = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            gemini_tools.append({
                "name": tool_name,
                "description": tool_info.get("description", ""),
                "parameters": parameters,
            })

        return gemini_tools

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
    def _extract_function_calls(response) -> list:
        """
        Return a list of function_call objects from a Gemini response,
        safely handling candidates whose finish_reason is MALFORMED_FUNCTION_CALL.
        """
        try:
            candidate = response.candidates[0]
        except (IndexError, AttributeError):
            return []

        finish_reason = getattr(candidate, "finish_reason", None)
        # finish_reason 12 == MALFORMED_FUNCTION_CALL — nothing to parse
        if finish_reason == _FINISH_REASON_MALFORMED_FUNCTION_CALL:
            logger.warning(
                "Gemini returned MALFORMED_FUNCTION_CALL (finish_reason=12). "
                "The model could not construct a valid tool call. "
                "Check that the tool schema is correct and all required fields are present."
            )
            return []

        parts = getattr(candidate.content, "parts", None) or []
        return [
            part.function_call
            for part in parts
            if hasattr(part, "function_call") and part.function_call.name
        ]

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
        if not self._model:
            self._initialize_gemini()

        history = conversation_history or []
        gemini_tools = self._convert_tools_to_gemini_format()

        tools_config = None
        if gemini_tools:
            tools_config = [
                genai.protos.Tool(
                    function_declarations=[
                        genai.protos.FunctionDeclaration(
                            name=t["name"],
                            description=t["description"],
                            parameters=self._dict_to_gemini_schema(t["parameters"]),
                        )
                        for t in gemini_tools
                    ]
                )
            ]

        chat = self._model.start_chat(
            history=self._convert_history_to_gemini(history)
        )

        # ------------------------------------------------------------------ #
        # Initial send                                                         #
        # ------------------------------------------------------------------ #
        try:
            response = await asyncio.to_thread(
                chat.send_message,
                message,
                tools=tools_config,
            )
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

            function_responses: list[genai.protos.Part] = []

            for fc in function_calls:
                tool_name = fc.name

                # Convert proto args to plain Python types before passing to MCP
                arguments: dict[str, Any] = _fc_args_to_python(fc)

                logger.debug(f"Tool call: {tool_name}({json.dumps(arguments, default=str)})")

                try:
                    result = await self.call_tool(tool_name, arguments)

                    content = result.content if hasattr(result, "content") else str(result)
                    if hasattr(content, "__iter__") and not isinstance(content, str):
                        content = "\n".join(
                            item.text if hasattr(item, "text") else str(item)
                            for item in content
                        )

                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": content},
                            )
                        )
                    )

                except Exception as e:
                    logger.error(f"Tool call failed for {tool_name}: {e}")
                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"error": str(e)},
                            )
                        )
                    )

            # Send all tool results back in one turn
            try:
                response = await asyncio.to_thread(
                    chat.send_message,
                    function_responses,
                    tools=tools_config,
                )
            except Exception as e:
                logger.error(f"Gemini send_message (tool response) failed: {e}")
                raise

        # ------------------------------------------------------------------ #
        # Extract final text                                                   #
        # ------------------------------------------------------------------ #
        response_text = ""
        try:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text
        except (IndexError, AttributeError):
            pass

        if not response_text:
            logger.warning("No text content in final Gemini response.")

        return response_text

    # ---------------------------------------------------------------------- #
    # Schema helpers                                                           #
    # ---------------------------------------------------------------------- #

    def _dict_to_gemini_schema(self, schema: dict[str, Any]) -> "genai.protos.Schema":
        """Recursively convert a sanitized schema dict to a genai.protos.Schema."""
        kwargs: dict[str, Any] = {
            "type": self._map_json_type_to_gemini(schema.get("type", "string")),
        }
        if "description" in schema:
            kwargs["description"] = schema["description"]
        if "items" in schema:
            kwargs["items"] = self._dict_to_gemini_schema(schema["items"])
        if "properties" in schema:
            kwargs["properties"] = {
                k: self._dict_to_gemini_schema(v)
                for k, v in schema["properties"].items()
            }
        if "required" in schema:
            kwargs["required"] = schema["required"]
        if "enum" in schema:
            kwargs["enum"] = schema["enum"]
        return genai.protos.Schema(**kwargs)

    def _map_json_type_to_gemini(self, json_type: str) -> int:
        """Map JSON schema types to Gemini proto types."""
        type_mapping = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT,
        }
        return type_mapping.get(json_type, genai.protos.Type.STRING)

    def _convert_history_to_gemini(
        self,
        history: list[dict[str, Any]],
    ) -> list[genai.protos.Content]:
        """Convert conversation history to Gemini format."""
        gemini_history = []

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            gemini_role = "user" if role == "user" else "model"

            gemini_history.append(
                genai.protos.Content(
                    role=gemini_role,
                    parts=[genai.protos.Part(text=content)],
                )
            )

        return gemini_history

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