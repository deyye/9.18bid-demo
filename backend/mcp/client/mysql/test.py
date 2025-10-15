import asyncio
import os
import sys
import contextlib
from typing import Any, Optional
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from rich import print as rprint


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.append(parent_parent_dir)
from utils.pretty import RICH_CONSOLE

class MCPClient:
    def __init__(self, server_params):
        self.server_params = server_params  # 服务器参数
        self.exit_stack = contextlib.AsyncExitStack()  # 初始化异步退出栈
        self.session = None  # 客户端会话
        self.stdio = None    # 标准IO传输
        self.write = None    # 写入方法
        self.tools = []      # 可用工具列表  
    
    async def cleanup(self):
        """清理资源"""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            print(f"清理资源时出错: {e}")
            RICH_CONSOLE.print_exception()
            return None

    def get_tools(self) -> list:
        """获取已缓存的工具列表（需在connect()后调用）"""
        if not self.tools:
            print("警告：工具列表为空，请先调用 connect() 连接服务器")
        return self.tools
    
    async def connect(self):
        """连接到服务器并完成初始化（替代_connect_to_server，作为公开方法）"""
        await self._connect_to_server()

    async def _connect_to_server(self) -> None:
        """连接到MCP服务器"""
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(self.server_params),
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools
        rprint("\nConnected to server with tools:", [tool.name for tool in self.tools])

    async def call_tool(self, name: str, params: dict[str, Any]):
        """调用工具（需在connect()后使用）"""
        if not self.session:
            raise ValueError("请先调用 connect() 连接服务器，再调用工具")
        return await self.session.call_tool(name, params)
    
async def main():
    server_params = StdioServerParameters(
        command='uv',
        args=['run', '/home/star/81/langgraph/backend/mcp/server/mysql/main.py'],
        env=None
    )
    mcp_client = MCPClient(server_params)

    try:
        await mcp_client.connect()
        tools = mcp_client.get_tools()
        rprint("Available tools:", [tool.name for tool in tools])

        if 'execute_sql' in [tool.name for tool in mcp_client.tools]:
            result = await mcp_client.call_tool(
                'execute_sql',
                {'query': 'SELECT * FROM users WHERE user_id = 1'}
            )
            rprint("工具调用结果:", result)
        else:
            rprint("未找到 execute_sql 工具")
    finally:
        await mcp_client.cleanup()
    

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断，程序退出")
    except Exception as e:
        print(f"\n程序异常退出: {e}")
        sys.exit(1)
