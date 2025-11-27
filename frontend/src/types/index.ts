/**
 * 类型定义
 */

// 配置数据结构
export interface ConfigData {
  modelName: string;
  apiKey: string;
}

// 步骤状态
export enum ProcessStep {
    DOCUMENT_ANALYSIS = 0,
    OUTLINE_EDIT = 1,
    CONTENT_GENERATE = 2,
    EXPORT = 3,
}

// 标书大纲章节数据模型
export interface OutlineItem {
    id: string;
    level: number;
    title: string;
    wordCount?: number; 
    children?: OutlineItem[];
    content?: string;
    description?: string;
}

// 应用状态
export interface AppState {
  currentStep: ProcessStep;
  config: ConfigData;
  documentContent: string; // 招标文件内容提取原文
  analysisResult: string;  // AI 分析结果（关键信息、评分要求）
  outline: OutlineItem[]; // 标书目录结构 (包含 wordCount)
  generatedContent: { [key: string]: string }; // 生成的内容，key为章节ID
}