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
    // ⚠️ 修正点 1：路径从 /analyze 改为 /analyze-stream
    // ⚠️ 修正点 2：添加查询参数 ?stream=false，让后端一次性返回结果，不要流式传输
    const response = await fetch(`${API_BASE_URL}/document/analyze-stream?stream=false`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        // ⚠️ 修正点 3：Body 结构必须匹配后端 AnalysisRequest 模型
        // 后端要求字段: file_content, analysis_type
        body: JSON.stringify({ 
            file_content: content,           // 之前是 document_content，必须改为 file_content
            analysis_type: "overview"        // 必须指定分析类型，可选 "overview" 或 "requirements"
        }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '文档分析失败');
    }

    const data = await response.json();
    // ⚠️ 修正点 4：后端返回结构是 { result: "..." }，而不是 analysis_result
    return data.result || '未获取到分析结果'; 
}

// ----------------------------------------------------
// 3. 目录生成 API
// ----------------------------------------------------

/**
 * @function generateOutline
 * @description 根据项目概述和技术要求，请求后端 AI 生成标书目录。
 * @param overview - 项目概述。
 * @param requirements - 技术评分要求。
 * @param config - 当前的 AI 配置。
 * @returns 标书目录结构 OutlineItem[]。
 */
export async function generateOutline(
    overview: string, 
    requirements: string, 
    config: AppState['config']
): Promise<OutlineItem[]> {
    // 假设后端路由: /api/outline/generate
    const response = await fetch(`${API_BASE_URL}/outline/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        // ✅ 修正：请求体必须匹配后端 OutlineRequest (overview, requirements)
        body: JSON.stringify({ 
            overview: overview, 
            requirements: requirements,
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
    return data.outline || []; 
}

// ----------------------------------------------------
// 4. 内容生成 API
// ----------------------------------------------------

/**
 * @function generateContent
 * @description 根据完整大纲请求后端 AI 生成所有章节内容。
 */
export async function generateContent(
    documentContent: string,
    overview: string,      // ✅ 新增参数
    requirements: string,  // ✅ 新增参数
    outline: OutlineItem[],
    config: AppState['config']
): Promise<{ [key: string]: string }> {
    
    // 为了确保生成内容时 AI 能看到所有上下文，我们将概述和要求合并传给 project_overview
    // (因为后端 ContentGenerationRequest 目前只有一个 project_overview 字段)
    const combinedOverview = `项目概述：\n${overview}\n\n技术评分要求：\n${requirements}`;

    const response = await fetch(`${API_BASE_URL}/content/generate-full-project`, { // 注意：这里使用了 generate-full-project 路由
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            // document_content: documentContent, // 后端 ContentGenerationRequest 似乎没定义这个，暂时注释或保留视后端情况而定
            project_overview: combinedOverview,   // ✅ 传入合并后的上下文
            outline: outline[0], // ⚠️ 注意：generate_controller.py 似乎期望单个根节点 (Dict)，如果 outline 是数组请传 outline[0] 或调整结构
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

    // 后端返回结构为 { contents: {...}, ... }
    const data = await response.json();
    return data.contents || {}; 
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

/**
 * 流式分析文档
 * @param content 文档内容
 * @param analysisType 分析类型 ('overview' | 'requirements')
 * @param onChunk 接收流式数据块的回调函数
 * @param onError 错误回调
 */
export async function analyzeDocumentStream(
    content: string,
    analysisType: 'overview' | 'requirements',
    onChunk: (chunk: string) => void,
    onError: (error: string) => void
): Promise<void> {
    try {
        // 1. 发起请求，开启 stream=true
        const response = await fetch(`${API_BASE_URL}/document/analyze-stream?stream=true&use_qwen=true`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                file_content: content,
                analysis_type: analysisType 
            }),
        });

        if (!response.ok) throw new Error(response.statusText);
        if (!response.body) throw new Error("ReadableStream not supported");

        // 2. 读取流
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            // 后端返回格式为: data: {"chunk": "..."}\n\n
            // 我们需要按行分割并解析
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6); // 去掉 "data: "
                    if (jsonStr.trim() === "[DONE]") continue; // 结束标识（如果有）
                    try {
                        const data = JSON.parse(jsonStr);
                        // 如果有 chunk 字段，就回调出去
                        if (data.chunk) {
                            onChunk(data.chunk);
                        }
                    } catch (e) {
                        console.warn("解析流数据失败", e);
                    }
                }
            }
        }
    } catch (err: any) {
        onError(err.message || "流式请求失败");
    }
}