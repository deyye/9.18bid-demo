import gradio as gr
import requests
import time
import json
from threading import Thread
import queue

# 后端API地址
BACKEND_URL = "http://localhost:8000"

# 用于流式响应的队列
response_queue = queue.Queue()

def set_api_config(api_key, base_url, model_name):
    """设置API配置"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/config/save",
            json={
                "api_key": api_key,
                "base_url": base_url,
                "model_name": model_name
            }
        )
        return "配置保存成功" if response.status_code == 200 else f"配置失败: {response.text}"
    except Exception as e:
        return f"配置错误: {str(e)}"

def upload_document(file):
    """上传文档并解析"""
    if not file:
        return "请上传文件"
    
    try:
        files = {"file": open(file.name, "rb")}
        response = requests.post(f"{BACKEND_URL}/api/document/upload", files=files)
        return response.json().get("content", "文档解析失败")
    except Exception as e:
        return f"上传错误: {str(e)}"

def analyze_document(content):
    """分析文档内容"""
    if not content:
        return "请先上传文档"
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/document/analyze",
            json={"content": content}
        )
        result = response.json()
        return result.get("overview", ""), result.get("requirements", "")
    except Exception as e:
        return f"分析错误: {str(e)}", ""

def generate_outline_stream(overview, requirements):
    """流式生成目录"""
    if not overview or not requirements:
        yield "请先完成文档分析"
        return
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/outline/generate-stream",
            json={"overview": overview, "requirements": requirements},
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8').replace('data: ', '')
                if data == "[DONE]":
                    break
                try:
                    json_data = json.loads(data)
                    full_response += json_data.get("chunk", "")
                    yield full_response
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"生成错误: {str(e)}"

def generate_content_stream(outline_item, context):
    """流式生成内容"""
    if not outline_item or not context:
        yield "请提供目录项和上下文"
        return
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/content/generate-stream",
            json={"outline_item": outline_item, "context": context},
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8').replace('data: ', '')
                if data == "[DONE]":
                    break
                try:
                    json_data = json.loads(data)
                    full_response += json_data.get("chunk", "")
                    yield full_response
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"生成错误: {str(e)}"

def create_interface():
    """创建Gradio界面"""
    with gr.Blocks(title="AI智能标书写作助手") as demo:
        gr.Markdown("# 📄 AI智能标书写作助手")
        
        with gr.Tab("1. 配置"):
            api_key = gr.Textbox(label="API Key", type="password")
            base_url = gr.Textbox(label="API Base URL", value="https://api.openai.com/v1")
            model_name = gr.Textbox(label="模型名称", value="gpt-3.5-turbo")
            config_btn = gr.Button("保存配置")
            config_status = gr.Textbox(label="配置状态", interactive=False)
            config_btn.click(set_api_config, [api_key, base_url, model_name], config_status)
        
        with gr.Tab("2. 文档上传与分析"):
            file_input = gr.File(label="上传招标文件 (Word或PDF)")
            upload_btn = gr.Button("上传并解析")
            doc_content = gr.Textbox(label="文档内容", lines=10, interactive=False)
            
            analyze_btn = gr.Button("分析文档")
            project_overview = gr.Textbox(label="项目概述", lines=5, interactive=False)
            tech_requirements = gr.Textbox(label="技术要求", lines=5, interactive=False)
            
            upload_btn.click(upload_document, file_input, doc_content)
            analyze_btn.click(analyze_document, doc_content, [project_overview, tech_requirements])
        
        with gr.Tab("3. 目录生成"):
            outline_inputs = [project_overview, tech_requirements]
            generate_outline_btn = gr.Button("生成目录")
            outline_output = gr.Textbox(label="标书目录", lines=10, interactive=False)
            generate_outline_btn.click(
                generate_outline_stream, 
                outline_inputs, 
                outline_output
            )
        
        with gr.Tab("4. 内容生成"):
            outline_item = gr.Textbox(label="选择目录项")
            context = gr.Textbox(label="上下文信息", lines=5)
            generate_content_btn = gr.Button("生成内容")
            content_output = gr.Textbox(label="生成的内容", lines=10, interactive=False)
            generate_content_btn.click(
                generate_content_stream,
                [outline_item, context],
                content_output
            )
    
    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860)