/**
 * 主应用组件
 */
import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Steps, Button, Drawer, message, Space } from 'antd';
import { SettingOutlined, LeftOutlined } from '@ant-design/icons';
import { AppState, ProcessStep } from './types';
import useAppState from './hooks/useAppState';
import DocumentAnalysis from './pages/DocumentAnalysis';
import OutlineEdit from './pages/OutlineEdit';
import ContentEdit from './pages/ContentEdit';
import ConfigPanel from './components/ConfigPanel';
import logo from './logo.svg';
import { AppStateProvider } from './hooks/useAppState';

const { Header, Content, Sider } = Layout;

// 流程步骤定义 (替代 StepBar.tsx)
const stepItems = [
    { title: '智能文档解析', description: '上传并分析招标文件' },
    { title: 'AI生成目录', description: '编辑并设置章节字数' },
    { title: '内容自动生成', description: '编辑和优化内容' },
    { title: '一键导出', description: 'Word 文档导出' },
];

// 主应用逻辑
const MainApp: React.FC = () => {
    const { state, setState } = useAppState();
    const navigate = useNavigate();
    const location = useLocation();
    
    const [configDrawerVisible, setConfigDrawerVisible] = useState(false);

    // 1. 同步 URL 和 State (当用户手动输入 URL 或浏览器后退时)
    React.useEffect(() => {
        let step = ProcessStep.DOCUMENT_ANALYSIS;
        if (location.pathname.includes('/outline')) step = ProcessStep.OUTLINE_EDIT;
        else if (location.pathname.includes('/content')) step = ProcessStep.CONTENT_GENERATE;
        
        // 只有当 state 不一致时才更新，避免死循环
        if (state.currentStep !== step) {
            setState({ currentStep: step });
        }
    }, [location.pathname, setState, state.currentStep]);

    // 2. 流程导航处理 (点击左侧菜单时触发)
    const handleStepChange = (step: number) => {
        // 限制：只能点击“已完成”或“当前”或“下一步”（可选，如果想随意跳转就把限制去掉）
        // 这里演示允许随意点击（只要流程通畅）
        
        let path = '/analysis';
        switch (step) {
            case ProcessStep.DOCUMENT_ANALYSIS: path = '/analysis'; break;
            case ProcessStep.OUTLINE_EDIT: path = '/outline'; break;
            case ProcessStep.CONTENT_GENERATE: path = '/content'; break;
            case ProcessStep.EXPORT: path = '/content'; break; // 导出通常在内容页操作
            default: path = '/analysis'; break;
        }

        // 更新状态并跳转
        setState({ currentStep: step });
        navigate(path);
    };

    // 导出 Word 逻辑
    const handleExport = () => {
        message.info('正在请求后端生成 Word 文档...');
        // 实际调用导出 API
        // exportToWord(state.generatedContent).then(...)
    };

    return (
        <Layout style={{ minHeight: '100vh' }}>
            {/* Header ... */}
            <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f0f0f0' }}>
                 <div style={{ display: 'flex', alignItems: 'center' }}>
                    <img src={logo} alt="Logo" style={{ height: 32, marginRight: 12 }} />
                    <h1 style={{ margin: 0, fontSize: '20px', color: '#1890ff' }}>智能标书写作助手</h1>
                </div>
                <Space>
                    <Button 
                        type="primary" 
                        onClick={handleExport} 
                        // 只有在内容生成步骤才允许导出
                        disabled={state.currentStep < ProcessStep.CONTENT_GENERATE}
                    >
                        一键导出 Word
                    </Button>
                    <Button 
                        icon={<SettingOutlined />} 
                        onClick={() => setConfigDrawerVisible(true)}
                        title="个性化定制"
                    >
                        配置
                    </Button>
                </Space>
            </Header>

            <Layout>
                <Sider width={250} style={{ background: '#fff', borderRight: '1px solid #f0f0f0', padding: '24px 16px' }}>
                    {/* ✅ 修正点：Steps 组件配置 */}
                    <Steps
                        direction="vertical"
                        current={state.currentStep} // 直接绑定 global state
                        onChange={handleStepChange} // 绑定点击事件
                        items={[
                            { 
                                title: '智能文档解析', 
                                description: '上传并分析招标文件',
                                // 允许点击的条件：总是允许，或者只允许已走过的步骤
                                disabled: false 
                            },
                            { 
                                title: 'AI生成目录', 
                                description: '编辑并设置章节字数',
                                // 只有当第一步完成后才允许点击（可选）
                                disabled: !state.documentContent && !state.overview
                            },
                            { 
                                title: '内容自动生成', 
                                description: '编辑和优化内容',
                                disabled: state.outline.length === 0
                            },
                            { 
                                title: '一键导出', 
                                description: 'Word 文档导出',
                                disabled: Object.keys(state.generatedContent).length === 0
                            },
                        ]}
                    />
                </Sider>

                <Content style={{ padding: 24, background: '#f5f5f5' }}>
                    <Routes>
                        {/* 修正 path，去掉 /analysis 的重复定义 */}
                        <Route path="/" element={<DocumentAnalysis onNext={() => handleStepChange(ProcessStep.OUTLINE_EDIT)} />} />
                        <Route path="/analysis" element={<DocumentAnalysis onNext={() => handleStepChange(ProcessStep.OUTLINE_EDIT)} />} />
                        <Route path="/outline" element={<OutlineEdit onNext={() => handleStepChange(ProcessStep.CONTENT_GENERATE)} />} />
                        <Route path="/content" element={<ContentEdit onNext={() => handleExport()} />} />
                    </Routes>
                </Content>
            </Layout>

            {/* Drawer ... */}
            <Drawer
                title="个性化定制 AI 模型"
                placement="right"
                onClose={() => setConfigDrawerVisible(false)}
                open={configDrawerVisible}
                width={400}
                footer={
                    <div style={{ textAlign: 'right' }}>
                        <Button onClick={() => setConfigDrawerVisible(false)} style={{ marginRight: 8 }}>
                            关闭
                        </Button>
                    </div>
                }
            >
                <ConfigPanel />
            </Drawer>
        </Layout>
    );
};

const RootApp: React.FC = () => (
    <Router>
        {/* 核心修改：使用 AppStateProvider 包装整个应用 */}
        <AppStateProvider>
            <MainApp />
        </AppStateProvider>
    </Router>
);

export default RootApp;
