import { AppState, OutlineItem } from '../types';

// API 基础路径
const API_BASE_URL = 'http://localhost:8000/api'; 

// ----------------------------------------------------
// 辅助类型定义
// ----------------------------------------------------

interface ConfigPayload {
    modelName: string;
    apiKey: string;
}

export interface DocumentUploadResponse {
    success: boolean;       // 后端返回字段
    message: string;        // 后端返回字段
    file_content: string | null;   // ✅ 修正：必须改为 file_content
    
    // 注意：目前的后端代码 schemas.py 中并没有返回 fileId 和 fileName
    // 如果后续流程不需要它们，可以忽略；如果需要，必须修改后端添加这些字段
    fileId?: string;        
    fileName?: string;
}

// ----------------------------------------------------
// 1. 配置相关 API
// ----------------------------------------------------

/**
 * @function saveConfig
 * @description 异步保存 AI 模型配置和 Key 到后端。
 */
export async function saveConfig(configPayload: ConfigPayload): Promise<void> {
    // 假设后端路由: /api/config/update
    const response = await fetch(`${API_BASE_URL}/config/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            // 假设后端配置结构为 api_key, model_name
            api_key: configPayload.apiKey,
            model_name: configPayload.modelName,
        }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '保存配置失败');
    }
}

// ----------------------------------------------------
// 2. 文档解析 API
// ----------------------------------------------------

/**
 * @function uploadDocument
 * @description 上传招标文件到后端。
 * @param file - 待上传的 File 对象。
 * @returns 包含文件ID、文件名和提取的文本内容的响应。
 */
export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    // 假设后端路由: /api/document/upload
    const response = await fetch(`${API_BASE_URL}/document/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '文件上传失败');
    }
    
    // 假设后端返回 { fileId: '...', fileName: '...', documentContent: '...' }
    return await response.json(); 
}

/**
 * @function analyzeDocument
 * @description 请求后端 AI 分析招标文件内容，提取关键信息。
 * @param content - 原始内容。
 * @param config - 当前的 AI 配置。
 * @returns 招标文件分析结果字符串。
 */
export async function analyzeDocument(content: string, config: AppState['config']): Promise<string> {
    // 假设后端路由: /api/document/analyze
    const response = await fetch(`${API_BASE_URL}/document/analyze`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            document_content: content, 
            config: {
                api_key: config.apiKey,
                model_name: config.modelName,
            }
        }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '文档分析失败');
    }

    const data = await response.json();
    return data.analysis_result || '未获取到分析结果'; // 假设返回 { analysis_result: '...' }
}

// ----------------------------------------------------
// 3. 目录生成 API
// ----------------------------------------------------

/**
 * @function generateOutline
 * @description 根据招标文件分析结果，请求后端 AI 生成标书目录。
 * @param analysisResult - 招标文件分析结果。
 * @param config - 当前的 AI 配置。
 * @returns 标书目录结构 OutlineItem[]。
 */
export async function generateOutline(analysisResult: string, config: AppState['config']): Promise<OutlineItem[]> {
    // 假设后端路由: /api/outline/generate
    const response = await fetch(`${API_BASE_URL}/outline/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            analysis_result: analysisResult, 
            config: {
                api_key: config.apiKey,
                model_name: config.modelName,
            }
        }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '生成目录失败');
    }

    const data = await response.json();
    return data.outline || []; // 假设后端返回 { outline: [...] }
}


// ----------------------------------------------------
// 4. 内容生成 API
// ----------------------------------------------------

/**
 * @function generateContent
 * @description 根据完整大纲（包含字数设定）请求后端 AI 生成所有章节内容。
 * @returns 包含所有章节内容的字典 { chapterId: content }。
 */
export async function generateContent(
    documentContent: string,
    analysisResult: string,
    outline: OutlineItem[],
    config: AppState['config']
): Promise<{ [key: string]: string }> {
    // 假设后端路由: /api/content/generate
    const response = await fetch(`${API_BASE_URL}/content/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            document_content: documentContent,
            analysis_result: analysisResult,
            outline: outline, 
            config: {
                api_key: config.apiKey,
                model_name: config.modelName,
            }
        }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '内容生成失败');
    }

    return await response.json(); // 假设后端返回 { chapterId: content, ... }
}


// ----------------------------------------------------
// 5. 导出 API
// ----------------------------------------------------

/**
 * @function exportToWord
 * @description 请求后端将所有内容打包导出为 Word 文档 (.docx)。
 */
export async function exportToWord(generatedContent: { [key: string]: string }, outline: OutlineItem[]): Promise<void> {
    // 假设后端路由: /api/document/export
    const response = await fetch(`${API_BASE_URL}/document/export`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: generatedContent, outline: outline }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '导出 Word 失败');
    }

    // 处理文件流下载
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '智能标书.docx';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
}