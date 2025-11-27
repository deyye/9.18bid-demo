// ⬇️ 修复：显式导入 React
import React, { createContext, useContext, useState, Dispatch, SetStateAction } from 'react';
import { AppState, ProcessStep } from '../types'; 

// 标书助手应用的默认初始状态
const initialAppState: AppState = {
    currentStep: ProcessStep.DOCUMENT_ANALYSIS,
    documentContent: '',
    
    // 🔴 删除: analysisResult: '', 
    // 🟢 新增:
    overview: '', 
    requirements: '',

    outline: [],
    generatedContent: {},
    config: {
        modelName: 'qwen3-14b',
        apiKey: '',
    },
};

// 定义更新函数的类型：支持“部分对象”或“函数式更新”
type StateUpdate = Partial<AppState> | ((prev: AppState) => Partial<AppState>);

// 1. 定义 Context 类型
interface AppContextType {
    state: AppState;
    setState: (update: StateUpdate) => void;
}

// 2. 创建 Context
const AppContext = createContext<AppContextType | undefined>(undefined);

// 3. AppState Provider 组件
export const AppStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [state, setState] = useState<AppState>(initialAppState);

    // 2. 增强 setState：支持函数式更新 (对于流式追加内容至关重要)
    const mergeState = (update: StateUpdate) => {
        setState((prevState) => {
            // 如果传入的是函数，则先执行函数获取部分更新数据
            const partialUpdate = typeof update === 'function' ? update(prevState) : update;
            // 合并状态
            return { ...prevState, ...partialUpdate };
        });
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