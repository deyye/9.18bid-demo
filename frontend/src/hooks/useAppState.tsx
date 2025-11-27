// ⬇️ 修复：显式导入 React
import React, { createContext, useContext, useState, Dispatch, SetStateAction } from 'react';
import { AppState, ProcessStep } from '../types'; 

// 标书助手应用的默认初始状态
const initialAppState: AppState = {
    currentStep: ProcessStep.DOCUMENT_ANALYSIS,
    documentContent: '',
    analysisResult: '',
    outline: [],
    generatedContent: {},
    config: {
        modelName: 'gpt-4o', // 默认模型
        apiKey: '',
    },
};

// 1. 定义 Context 类型 (关键修改在这里)
interface AppContextType {
    state: AppState;
    // ⬇️ 修复 TS2345 错误: 允许传入 Partial<AppState> 进行合并更新
    setState: (update: Partial<AppState>) => void;
}

// 2. 创建 Context
const AppContext = createContext<AppContextType | undefined>(undefined);

// 3. AppState Provider 组件
export const AppStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [state, setState] = useState<AppState>(initialAppState);

    // ⬇️ 新增：实现状态合并逻辑
    const mergeState = (update: Partial<AppState>) => {
        setState(prevState => ({ ...prevState, ...update } as AppState));
    };

    return (
        <AppContext.Provider value={{ state, setState: mergeState }}> 
            {children}
        </AppContext.Provider>
    );
};

// 4. 自定义 Hook：使用默认导出 (Default Export)
const useAppState = (): AppContextType => {
    const context = useContext(AppContext);
    if (context === undefined) {
        throw new Error('useAppState 必须在 AppStateProvider 内部使用');
    }
    return context;
};

export default useAppState;