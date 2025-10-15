from typing import Annotated

from langchain.chat_models import init_chat_model
from langchain_ollama import ChatOllama
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)


# llm = init_chat_model("anthropic:claude-3-5-sonnet-latest") # 改成本地部署的模型
llm = ChatOllama(base_url="http://localhost:11434", model="qwen3:14b")

def chatbot(state: State):
    print("assistant: ", end="", flush=True)  # 先打印前缀
    chunks = []
    for chunk in llm.stream(state["messages"]):  # 启用流式调用
        content_piece = chunk.content  # 每次返回的部分文本
        print(content_piece, end="", flush=True)  # 实时打印
        chunks.append(content_piece)
    return {"messages": [{"role": "assistant", "content": "".join(chunks)}]}


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

if __name__ == "__main__":
    user_input = {"role": "user", "content": "你好"}
    
    # 执行图
    final_state = graph.invoke({"messages": [user_input]})
    
    print("对话历史:")
    for msg in final_state["messages"]:
        print(f"{msg.type}: {msg.content}")
    
    from IPython.display import Image, display

    try:
        display(Image(graph.get_graph().draw_mermaid_png()))
    except Exception:
        # This requires some extra dependencies and is optional
        pass