from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import FileUploadResponse
from markitdown import MarkItDown
import tempfile
import os
import json

router = APIRouter(prefix="/api/pdf", tags=["文档解析"])

class MarkItDownService:
    def __init__(self, endpoint: str = "<document_intelligence_endpoint>"):
        self.endpoint = endpoint
        self.md = MarkItDown(
            docintel_endpoint=self.endpoint,
            enable_plugins=["image"],
            ocr_enabled=True,
            ocr_langs=["eng", "chi_sim"]  # 英文+简体
        )

    def convert(self, file_path: str) -> str:
        result = self.md.convert(file_path)
        return result.text_content

    def ping(self) -> bool:
        if not self.endpoint:
            raise ValueError("文档智能端点未配置")
        return True
    
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文档并通过MarkItDownService提取文本内容"""
    # 临时文件路径
    temp_file_path = None

    try:
        # --------------------------
        # 1. 保留原文件类型校验（仅支持PDF/Word）
        # --------------------------
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg", "image/png", "image/gif", "image/bmp"
        ]  # Word(.docx)
        allowed_extensions = {'.pdf', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return FileUploadResponse(
                success=False,
                message=f"不支持的文件扩展名[{file_ext}]，请上传PDF、Word或常见图片格式"
            )

        # --------------------------
        # 2. 保存上传文件到临时路径（供MarkItDown转换）
        # --------------------------
        # 创建临时文件（delete=False：手动控制删除，避免转换时文件被自动清理）
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name  # 记录临时文件路径
            # 读取上传文件内容并写入临时文件（异步读取流）
            file_content = await file.read()
            temp_file.write(file_content)

        # --------------------------
        # 3. 初始化MarkItDownService并校验端点
        # --------------------------
        markdown_service = MarkItDownService()
        try:
            # 前置校验端点可用性
            markdown_service.ping()
        except ValueError as e:
            return FileUploadResponse(
                success=False,
                message=f"文档处理服务不可用：{str(e)}（请检查端点配置）"
            )

        # --------------------------
        # 4. 调用MarkItDown转换文档为文本
        # --------------------------
        converted_text = markdown_service.convert(temp_file_path)
        # converted_text = converted_text.strip()

        # --------------------------
        # 5. 成功响应
        # --------------------------
        return FileUploadResponse(
            success=True,
            message=f"文件[{file.filename}]上传并转换成功（提取文本长度：{len(converted_text)}字符）",
            file_content=converted_text  # 返回转换后的文本内容
        )

    # --------------------------
    # 异常处理（细化错误场景）
    # --------------------------
    except Exception as e:
        error_msg = f"文件处理失败：{str(e)}"
        # 区分不同异常类型（可选，返回更精准的提示）
        if "MarkItDown" in str(type(e)):
            error_msg = f"文档转换失败（MarkItDown服务错误）：{str(e)}"
        elif "tempfile" in str(type(e)):
            error_msg = f"临时文件处理失败：{str(e)}"
        return FileUploadResponse(
            success=False,
            message=error_msg
        )

    # --------------------------
    # 最终清理：无论成功/失败，删除临时文件
    # --------------------------
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as clean_e:
                # 临时文件清理失败不影响主流程，仅日志记录（建议项目添加日志模块）
                print(f"警告：临时文件[{temp_file_path}]清理失败：{str(clean_e)}")