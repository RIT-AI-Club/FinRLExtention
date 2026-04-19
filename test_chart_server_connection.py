
import asyncio
import logging
from src.backend.mcp_client import MCPClient, MCPServerConfig

async def test_chart_server():
    logging.basicConfig(level=logging.DEBUG)
    client = MCPClient()
    
    # Manually configure the chart server to isolate it
    chart_server_cfg = MCPServerConfig(
        name="chart_generation",
        command="python",
        args=["src/backend/mcp_servers/mcp_chart_generation/server.py"]
    )
    
    try:
        print(f"Connecting to {chart_server_cfg.name}...")
        session = await client.connect_to_server(chart_server_cfg)
        print("Connected! Initializing discovery...")
        client.sessions[chart_server_cfg.name] = session
        tools = await client.discover_tools()
        print(f"Discovered tools: {list(tools.keys())}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_chart_server())
