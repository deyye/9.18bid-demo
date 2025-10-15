import anyio
import json
import re
from typing import Any, Dict, List
import aiohttp
from rich import print as rprint

from client.mysql.test import MCPClient, StdioServerParameters

def set_to_list_serializer(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def extract_json_block(text: str) -> dict:
    """
    从模型输出中提取第一个合法 JSON 对象（忽略 <think> 块或自然语言）。
    """
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        raise ValueError("未找到JSON结构")
    
    json_str = json_match.group(0).strip()
    return json.loads(json_str)

class QwenWithMCP:
    def __init__(self, server_params, model_server_url="http://localhost:10086"):
        self.mcp_client = MCPClient(server_params)
        self.model_server_url = model_server_url  # vLLM服务地址
        self.tools_schema = []  # 工具描述 schema

    # async def initialize(self):
    #     """初始化MCP连接并生成工具描述"""
    #     await self.mcp_client.connect()
    #     self._generate_tools_schema()

    async def initialize(self):
        await self.mcp_client.connect()
        self._generate_tools_schema()
       
    
    def _generate_tools_schema(self):
        """将MCP工具转换为模型可理解的JSON Schema"""
        for tool in self.mcp_client.tools:
            # 修复：将tool_schema缩进至for循环内，确保每个工具都被添加
            tool_schema = {
                "name": tool.name,
                "description": tool.description.strip(), 
                "parameters": {
                    "type": tool.inputSchema.get("type", "object"),
                    "properties": tool.inputSchema.get("properties", {}),
                    "required": tool.inputSchema.get("required", [])
                }
            }
            self.tools_schema.append(tool_schema)

    def _build_prompt(self, question: str) -> List[Dict]:
        """构建符合vLLM服务要求的消息格式"""
        tools_desc = json.dumps(self.tools_schema, indent=2, ensure_ascii=False, sort_keys=False)
        rprint(f"[bold magenta]工具描述：[/bold magenta]{tools_desc}")
        system_prompt = f"""
你是一名能够自主使用工具解决问题的智能助手。

以下是你可使用的工具清单（每个工具都附带描述与参数定义）：
{tools_desc}

使用规则：
1. 你必须依靠这些工具和已有信息**独立完成任务**，不得要求用户提供额外数据或操作。
2. 如果任务需要外部数据，请优先调用合适的工具获取，不要让用户补充。
3. 工具调用格式固定如下：
   <tool_call>{{"name": "工具名", "parameters": {{ "参数键值对" }}}}</tool_call>
4. 工具调用完成后，你将收到工具的执行结果，请基于该结果继续推理或生成最终回答。
5. 如果任务可在多轮工具调用后解决，请自主循环推理和调用，直到得到最终完整答案。
6. 当你认为问题已经被充分、准确地解决时，再输出最终回答。

请始终保持：
- 不编造虚假信息；
- 不依赖用户输入的额外上下文；
- 不输出工具调用格式以外的控制标记；
- 每次回答都应尽可能完整、明确、具可执行性。

你的目标：**独立、可靠地完成用户的指令或问题解答**。
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]

    async def _call_model(self, messages: List[Dict]) -> str:
        """调用本地vLLM服务的/chat/completions接口"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "Qwen3-14B",
                "messages": messages,
                "temperature": 0.6,
                "stream": False
            }
            async with session.post(
                f"{self.model_server_url}/chat/completions",
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"模型调用失败: {await response.text()}")
                result = await response.json()
                rprint(f"模型响应（原始）：{result}")
                return result["generated_text"]

    async def _process_tool_call(self, tool_call: Dict[str, Any]) -> str:
        """执行 MCP 工具调用"""
        try:
            result = await self.mcp_client.call_tool(
                name=tool_call["name"],
                params=tool_call["parameters"],
            )
            rprint(f"[bold cyan]工具调用结果：[/bold cyan]{result}")
            return result
        except Exception as e:
            return f"工具调用失败：{str(e)}"

    async def _loop_until_satisfied(self, question: str) -> str:
        """循环调用模型和工具，直到回答被模型验证为满意"""
        messages = self._build_prompt(question)

        for round_idx in range(5):  # 最多循环5轮
            rprint(f"\n[bold green]=== 第 {round_idx+1} 轮推理开始 ===[/bold green]")

            # 1. 调用模型
            response = await self._call_model(messages)
            messages.append({"role": "assistant", "content": response})

            # 2. 多工具调用
            tool_call_matches = re.findall(r"<tool_call>(.*?)</tool_call>", response, re.S)
            if tool_call_matches:
                # 遍历所有提取到的工具调用
                for tool_json_str in tool_call_matches:
                    tool_json_str = tool_json_str.strip()
                    try:
                        tool_call = json.loads(tool_json_str)
                        rprint(f"[bold magenta]检测到工具调用请求：[/bold magenta]{tool_call}")
                        tool_result = await self._process_tool_call(tool_call)
                        # 将当前工具的结果添加到消息历史
                        messages.append({
                            "role": "user",
                            "content": f"工具返回结果如下：{tool_result}\n请基于该结果继续处理后续步骤"
                        })
                    except json.JSONDecodeError:
                        rprint(f"[red]❌ 工具调用解析失败：{tool_json_str}[/red]")
                        messages.append({
                            "role": "user",
                            "content": f"你刚才的工具调用JSON格式无效：{tool_json_str}，请重新输出"
                        })
                continue

            # 3. 模型自检阶段
            verify_prompt = (
                "请判断上面的回答是否已经充分、准确地解决了用户的问题。"
                "仅输出一个JSON对象，例如："
                '{"satisfied": true, "reason": "回答完整"}, '
                '或 {"satisfied": false, "reason": "遗漏了关键信息"}。'
            )

            verify_messages = messages + [{"role": "user", "content": verify_prompt}]
            verify_response = await self._call_model(verify_messages)
            rprint(f"[blue]🧩 模型自检输出：{verify_response}")

            try:
                verify_result = extract_json_block(verify_response)
                satisfied = verify_result.get("satisfied", False)
            except json.JSONDecodeError:
                rprint("[red]⚠️ 模型未返回有效JSON格式，视为未通过自检[/red]")
                satisfied = False
                verify_result = {"reason": "模型返回非JSON格式"}

            # 4. 判断自检结果
            if satisfied:
                rprint("[bold green]✅ 模型自检通过，回答满意[/bold green]")
                return response
            else:
                reason = verify_result.get("reason", "未说明原因")
                rprint(f"[yellow]🔁 模型认为回答不完整，将继续改进: {reason}[/yellow]")
                messages.append({
                    "role": "user",
                    "content": f"请根据上述自检意见（{reason}），改进并重新给出更完整、更准确的回答。"
                })

        # 超过循环上限仍未满意
        rprint("[red]⚠️ 达到最大循环次数，输出最后结果[/red]")
        return response

    async def answer(self, question: str) -> str:
        """外部调用入口"""
        return await self._loop_until_satisfied(question)


# === 主程序 ===
async def main():
    server_params = StdioServerParameters(
        command='uv',
        args=['run', '/home/star/81/langgraph/backend/mcp/server/mysql/main.py'],
        env=None,
    )
    qwen_mcp = QwenWithMCP(server_params)
    await qwen_mcp.initialize()

    question = "你看看数据库中有没有手机相关的数据"
    rprint(f"[bold blue]用户问题：[/bold blue]{question}")

    answer = await qwen_mcp.answer(question)
    rprint(f"\n[bold white on blue]最终回答：[/bold white on blue] {answer}")

    await qwen_mcp.mcp_client.cleanup()


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        print("\n用户中断，程序退出")
    except Exception as e:
        print(f"\n程序异常退出: {e}")