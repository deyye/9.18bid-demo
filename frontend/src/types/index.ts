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
  documentContent: string; 
  
  // 🔴 删除或弃用 analysisResult
  // analysisResult: string; 

  // 🟢 新增两个字段
  overview: string;        // 项目概述
  requirements: string;    // 技术评分要求
  
  outline: OutlineItem[]; 
  generatedContent: { [key: string]: string }; 

  isGenerating?: boolean;
}