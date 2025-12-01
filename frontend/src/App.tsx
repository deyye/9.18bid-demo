import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Steps, Button, Drawer, message, Space } from 'antd';
import { SettingOutlined, DatabaseOutlined } from '@ant-design/icons'; 
import { AppState, ProcessStep } from './types';
import useAppState, { AppStateProvider } from './hooks/useAppState';
import DocumentAnalysis from './pages/DocumentAnalysis';
import OutlineEdit from './pages/OutlineEdit';
import ContentEdit from './pages/ContentEdit';
import KnowledgeBase from './pages/KnowledgeBase';
import ConfigPanel from './components/ConfigPanel';
import logo from './logo.svg';

const { Header, Content, Sider } = Layout;

const MainApp: React.FC = () => {
    const { state, setState } = useAppState();
    const navigate = useNavigate();
    const location = useLocation();
    const [configDrawerVisible, setConfigDrawerVisible] = useState(false);

    // 1. 同步 URL 和 State
    React.useEffect(() => {
        let step = ProcessStep.DOCUMENT_ANALYSIS;
        if (location.pathname.includes('/outline')) step = ProcessStep.OUTLINE_EDIT;
        else if (location.pathname.includes('/content')) step = ProcessStep.CONTENT_GENERATE;
        // 如果是 knowledge 页面，保持 step 不变或设为 -1，这里简单保持原样即可
        
        if (!location.pathname.includes('/knowledge') && state.currentStep !== step) {
            setState({ currentStep: step });
        }
    }, [location.pathname, setState, state.currentStep]);

    // 2. 流程导航处理
    const handleStepChange = (step: number) => {
        let path = '/analysis';
        switch (step) {
            case ProcessStep.DOCUMENT_ANALYSIS: path = '/analysis'; break;
            case ProcessStep.OUTLINE_EDIT: path = '/outline'; break;
            case ProcessStep.CONTENT_GENERATE: path = '/content'; break;
            default: path = '/analysis'; break;
        }
        setState({ currentStep: step });
        navigate(path);
    };

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f0f0f0', position: 'sticky', top: 0, zIndex: 1000 }}>
                 <div style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }} onClick={() => navigate('/')}>
                    <img src={logo} alt="Logo" style={{ height: 32, marginRight: 12 }} />
                    <h1 style={{ margin: 0, fontSize: '20px', color: '#1890ff' }}>智能标书写作助手</h1>
                </div>
                <Space>
                    {/* 🟢 新增：知识库入口按钮 */}
                    <Button 
                        icon={<DatabaseOutlined />} 
                        onClick={() => navigate('/knowledge')}
                    >
                        企业知识库
                    </Button>
                    
                    <Button 
                        icon={<SettingOutlined />} 
                        onClick={() => setConfigDrawerVisible(true)}
                    >
                        配置
                    </Button>
                </Space>
            </Header>

            <Layout>
                {/* 只有在非知识库页面才显示侧边栏 */}
                {!location.pathname.includes('/knowledge') && (
                    <Sider width={250} style={{ background: '#fff', borderRight: '1px solid #f0f0f0', padding: '24px 16px', overflowY: 'auto', height: 'calc(100vh - 64px)', position: 'fixed', left: 0 }}>
                        <Steps
                            direction="vertical"
                            current={state.currentStep}
                            onChange={handleStepChange}
                            items={[
                                { title: '智能文档解析', description: '上传并分析招标文件', disabled: false },
                                { title: 'AI生成目录', description: '编辑并设置章节字数', disabled: !state.documentContent && !state.overview },
                                { title: '内容自动生成', description: '编辑和优化内容', disabled: state.outline.length === 0 },
                                { title: '一键导出', description: 'Word 文档导出', disabled: Object.keys(state.generatedContent).length === 0 },
                            ]}
                        />
                    </Sider>
                )}

                {/* 内容区域：根据是否显示侧边栏调整 padding */}
                <Content style={{ 
                    padding: 24, 
                    background: '#f5f5f5', 
                    marginLeft: location.pathname.includes('/knowledge') ? 0 : 250, 
                    marginTop: 0,
                    minHeight: 'calc(100vh - 64px)'
                }}>
                    <Routes>
                        <Route path="/" element={<DocumentAnalysis onNext={() => handleStepChange(ProcessStep.OUTLINE_EDIT)} />} />
                        <Route path="/analysis" element={<DocumentAnalysis onNext={() => handleStepChange(ProcessStep.OUTLINE_EDIT)} />} />
                        <Route path="/outline" element={<OutlineEdit onNext={() => handleStepChange(ProcessStep.CONTENT_GENERATE)} />} />
                        <Route path="/content" element={<ContentEdit onNext={() => {}} />} />
                        {/* 🟢 新增路由 */}
                        <Route path="/knowledge" element={<KnowledgeBase />} />
                    </Routes>
                </Content>
            </Layout>

            <Drawer
                title="个性化定制 AI 模型"
                placement="right"
                onClose={() => setConfigDrawerVisible(false)}
                open={configDrawerVisible}
                width={400}
            >
                <ConfigPanel />
            </Drawer>
        </Layout>
    );
};

const RootApp: React.FC = () => (
    <Router>
        <AppStateProvider>
            <MainApp />
        </AppStateProvider>
    </Router>
);

export default RootApp;