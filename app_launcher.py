import subprocess
import time
import threading
import webbrowser

def run_backend():
    """启动FastAPI后端"""
    subprocess.run(["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"])

def run_frontend():
    """启动Gradio前端"""
    time.sleep(3)  # 等待后端启动
    webbrowser.open("http://localhost:7860")
    subprocess.run(["python", "frontend-gradio/app.py"])

if __name__ == "__main__":
    # 启动后端
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # 启动前端
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    frontend_thread.start()
    
    # 保持主进程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("程序退出")