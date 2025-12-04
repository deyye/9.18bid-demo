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
    // ✅ 修正点：路径必须加上 /generate，与后端 router.post("/generate") 对应
    const response = await fetch(`${API_BASE_URL}/outline/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            overview: overview, 
            requirements: requirements,
            // 注意：后端 OutlineRequest 模型其实只定义了 overview 和 requirements
            // 传入 config 通常会被 Pydantic 忽略（不会报错），但为了严谨，确保后端能处理或忽略它
            config: {
                api_key: config.apiKey,
                model_name: config.modelName,
            }
        }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        // 增加更详细的错误提示，方便调试
        throw new Error(errorData.detail || `生成目录失败 (${response.status})`);
    }

    const data = await response.json();
    // 后端返回的是 OutlineResponse(outline=[...])，所以这里取 data.outline
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
            outline: outline, // ⚠️ 注意：generate_controller.py 似乎期望单个根节点 (Dict)，如果 outline 是数组请传 outline[0] 或调整结构
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

/**
 * @function generateContentStream
 * @description 流式并发生成所有章节内容。后端每生成好一个章节，就会通过 onChapterGenerated 回调一次。
 * @param documentContent 原文内容（可选）
 * @param overview 项目概述
 * @param requirements 技术要求
 * @param outline 目录结构
 * @param config 配置
 * @param onChapterGenerated 回调函数：接收 (chapterId, content)
 */
export async function generateContentStream(
    documentContent: string,
    overview: string,
    requirements: string,
    outline: OutlineItem[],
    config: AppState['config'],
    onChapterGenerated: (chapterId: string, content: string) => void
): Promise<void> {
    
    const combinedOverview = `项目概述：\n${overview}\n\n技术评分要求：\n${requirements}`;

    // 1. 发起流式请求
    const response = await fetch(`${API_BASE_URL}/content/generate-full-project?use_qwen=true`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            project_overview: combinedOverview,
            outline: outline, // 传入根节点
            config: {
                api_key: config.apiKey,
                model_name: config.modelName,
            }
        }),
    });

    if (!response.ok) {
        throw new Error(`内容生成服务连接失败: ${response.statusText}`);
    }
    
    if (!response.body) throw new Error("ReadableStream not supported");

    // 2. 读取流数据
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const jsonStr = line.slice(6).trim();
                if (jsonStr === "[DONE]") break;
                if (!jsonStr) continue;

                try {
                    const data = JSON.parse(jsonStr);
                    // 如果该章节生成成功，调用回调更新状态
                    if (data.success && data.chapter_id && data.content) {
                        onChapterGenerated(data.chapter_id, data.content);
                    } else if (!data.success) {
                        console.error(`章节 ${data.chapter_id} 生成失败: ${data.error}`);
                    }
                } catch (e) {
                    console.warn("解析流数据失败", e);
                }
            }
        }
    }
}

// ----------------------------------------------------
// 6. 知识库管理 API
// ----------------------------------------------------

export interface KnowledgeResponse {
    success: boolean;
    message: string;
    chunks_added?: number;
}

export interface SearchResult {
    query: string;
    results: any; 
}

// ✅ 修改：使用 XMLHttpRequest 支持上传进度监听
export async function uploadKnowledge(
    file: File, 
    docType: string = 'general',
    onProgress?: (percent: number) => void
): Promise<KnowledgeResponse> {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);
        
        xhr.open('POST', `${API_BASE_URL}/knowledge/upload?doc_type=${docType}`);
        
        // 监听上传进度
        if (xhr.upload && onProgress) {
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percent = Math.round((event.loaded / event.total) * 100);
                    onProgress(percent);
                }
            };
        }

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    resolve(response);
                } catch (e) {
                    reject(new Error('服务器返回数据格式错误'));
                }
            } else {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    reject(new Error(errorData.detail || '上传失败'));
                } catch (e) {
                    reject(new Error(`上传失败 (${xhr.status})`));
                }
            }
        };

        xhr.onerror = () => reject(new Error('网络请求失败'));
        
        xhr.send(formData);
    });
}

export async function resetKnowledge(): Promise<KnowledgeResponse> {
    const response = await fetch(`${API_BASE_URL}/knowledge/reset`, { method: 'POST' });
    if (!response.ok) throw new Error('重置失败');
    return await response.json();
}

export async function searchKnowledge(query: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/knowledge/test-search?query=${encodeURIComponent(query)}`, { method: 'POST' });
    if (!response.ok) throw new Error('检索失败');
    return await response.json();
}

export async function getKnowledgeList(limit: number = 20, offset: number = 0): Promise<{ total: number, items: any[] }> {
    const response = await fetch(`${API_BASE_URL}/knowledge/list?limit=${limit}&offset=${offset}`);
    if (!response.ok) throw new Error('获取列表失败');
    return await response.json();
}

export async function deleteKnowledgeFile(source: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/knowledge/delete?source=${encodeURIComponent(source)}`, {
        method: 'DELETE',
    });
    if (!response.ok) throw new Error('删除失败');
}

// ----------------------------------------------------
// 7. 结构化数据管理 API (新增)
// ----------------------------------------------------

export async function getAvailableTables(): Promise<{ tables: Array<{ name: string, description: string }> }> {
    const response = await fetch(`${API_BASE_URL}/data/tables`);
    if (!response.ok) throw new Error('获取可用表列表失败');
    return await response.json();
}

// --- t_company CRUD 示例 ---

export async function listTableRecords(tableName: string, limit: number = 10, offset: number = 0): Promise<{ total: number, items: any[] }> {
    // 动态拼接 tableName 到 URL
    const response = await fetch(`${API_BASE_URL}/data/${tableName}/list?limit=${limit}&offset=${offset}`);
    if (!response.ok) throw new Error(`查询表 ${tableName} 记录失败`);
    return await response.json();
}

export async function createCompanyRecord(data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/data/t_company`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '新增记录失败');
    }
    return await response.json();
}

export async function updateCompanyRecord(id: string, data: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/data/t_company/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '更新记录失败');
    }
    return await response.json();
}

export async function deleteRecord(tableName: string, recordId: string): Promise<{ success: boolean }> {
    const response = await fetch(`${API_BASE_URL}/data/${tableName}/${recordId}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '删除记录失败');
    }
    return await response.json();
}

/**
 * @function regenerateSingleChapter
 * @description 重新生成单个章节，支持用户指令和参考旧内容
 */
export async function regenerateSingleChapter(
    chapter: OutlineItem,
    parentChapters: OutlineItem[], // 上级章节列表
    overview: string,
    requirements: string,
    regenerationPrompt: string, // 用户指令
    originalContent: string,    // 旧内容
    config: AppState['config'],
    onChunk: (content: string) => void
): Promise<void> {
    
    const combinedOverview = `项目概述：\n${overview}\n\n技术评分要求：\n${requirements}`;

    const response = await fetch(`${API_BASE_URL}/content/generate-single-chapter?use_qwen=true`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            chapter: chapter,
            parent_chapters: parentChapters,
            project_overview: combinedOverview,
            regeneration_prompt: regenerationPrompt, // 🟢 传给后端
            original_content: originalContent,       // 🟢 传给后端
            config: {
                api_key: config.apiKey,
                model_name: config.modelName,
            }
        }),
    });

    if (!response.ok) {
        throw new Error(`重写服务连接失败: ${response.statusText}`);
    }
    
    if (!response.body) throw new Error("ReadableStream not supported");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const jsonStr = line.slice(6).trim();
                if (jsonStr === "[DONE]") break;
                if (!jsonStr) continue;

                try {
                    const data = JSON.parse(jsonStr);
                    if (data.status === 'streaming' && data.content) {
                        onChunk(data.content); // 实时回调流式片段
                    } else if (data.status === 'completed' && data.content) {
                        // 最终内容（包含清洗后的）
                        // onChunk(data.content); 
                    } else if (data.status === 'error') {
                        console.error(`生成错误: ${data.message}`);
                    }
                } catch (e) {
                    console.warn("解析流数据失败", e);
                }
            }
        }
    }
}