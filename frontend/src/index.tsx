import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, App as AntdApp } from 'antd'; 
import App from './App';
import './index.css'; // ⬇️ 正确的导入 CSS 方式！
import reportWebVitals from './reportWebVitals'; // 假设您有这个文件

// 使用 React 18 的创建根节点 API
const rootElement = document.getElementById('root');

if (rootElement) {
    ReactDOM.createRoot(rootElement).render(
        <React.StrictMode>
            {/* 1. 使用 ConfigProvider 进行主题配置 */}
            <ConfigProvider
                theme={{
                    token: {
                        colorPrimary: '#1890ff', // Ant Design 主题色
                    },
                }}
            >
                {/* 2. 使用 AntdApp 包裹，以便全局使用 message/notification/modal */}
                <AntdApp>
                    <App />
                </AntdApp>
            </ConfigProvider>
        </React.StrictMode>
    );
}

// 报告性能指标
reportWebVitals();