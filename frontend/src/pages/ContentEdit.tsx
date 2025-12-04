import React, { useState, useEffect, useRef } from 'react';
import { Button, Select, message, Spin, Typography, Layout as AntdLayout, Space, Empty, Tag, Modal, Input } from 'antd';
import { FileWordOutlined, ReloadOutlined, EditOutlined, LoadingOutlined, CheckCircleOutlined, DatabaseOutlined, SendOutlined } from '@ant-design/icons';
import useAppState from '../hooks/useAppState';
import { exportToWord, regenerateSingleChapter } from '../services/api';

// 引入 ReactQuill 及样式
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { OutlineItem } from '../types';

// 🟢 关键修复：创建一个避开类型检查的 Quill 包装器
const QuillWrapper = ReactQuill as any;
const { Title, Text } = Typography;
const { Content } = AntdLayout;
const { TextArea } = Input;

interface ContentEditProps {
    onNext: () => void;
}

// --- 自定义样式：模拟 A4 纸张和 Word 风格 ---
const editorStyles = `
    /* 整体背景 */
    .editor-layout {
        background-color: #f0f2f5;
        min-height: 100vh;
    }

    /* A4 纸张容器 */
    .a4-paper-container {
        width: 210mm; /* A4 宽度 */
        min-height: 297mm; /* A4 高度 */
        margin: 24px auto;
        background: white;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        padding: 0; /* 内边距由 Quill 内部控制 */
        position: relative;
        display: flex;
        flex-direction: column;
    }

    /* Quill 编辑器定制 */
    .quill-editor {
        flex: 1;
        display: flex;
        flex-direction: column;
    }

    /* 工具栏吸顶效果 */
    .ql-toolbar.ql-snow {
        position: sticky;
        top: 0;
        z-index: 100;
        background: #f8f9fa;
        border: none !important;
        border-bottom: 1px solid #ddd !important;
        padding: 12px 8px !important;
        text-align: center;
    }

    /* 编辑区域 */
    .ql-container.ql-snow {
        border: none !important;
        flex: 1;
        font-family: 'Songti SC', 'SimSun', serif; /* 宋体更像标书 */
        font-size: 16px;
    }

    .ql-editor {
        padding: 25.4mm 31.8mm; /* 标准公文页边距：上下2.54cm，左右3.18cm */
        line-height: 1.8; /* 宽松行高 */
        min-height: 250mm;
    }

    /* 标题样式增强 */
    .ql-editor h1 { font-size: 24px; font-weight: bold; margin-bottom: 16px; }
    .ql-editor h2 { font-size: 20px; font-weight: bold; margin-top: 12px; margin-bottom: 12px; }
    .ql-editor h3 { font-size: 18px; font-weight: bold; }
    .ql-editor p { margin-bottom: 8px; text-indent: 2em; } /* 首行缩进 */
`;

// --- Quill 工具栏配置 ---
const modules = {
    toolbar: [
        [{ 'header': [1, 2, 3, false] }],
        ['bold', 'italic', 'underline', 'strike'],
        [{ 'color': [] }, { 'background': [] }],
        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
        [{ 'indent': '-1'}, { 'indent': '+1' }],
        [{ 'align': [] }],
        ['clean']
    ],
};

const formats = [
    'header',
    'bold', 'italic', 'underline', 'strike',
    'color', 'background',
    'list', 'bullet', 'indent',
    'align'
];

const ContentEdit: React.FC<ContentEditProps> = ({ onNext }) => {
    const { state, setState } = useAppState();
    const [loading, setLoading] = useState(false);
    const [selectedChapterId, setSelectedChapterId] = useState<string | undefined>(undefined);
    
    const [isRegenModalOpen, setIsRegenModalOpen] = useState(false);
    const [regenPrompt, setRegenPrompt] = useState('');
    const [isRegenerating, setIsRegenerating] = useState(false);

    // 🟢 核心修复1：使用 ref 缓存流式内容，避免频繁渲染
    const streamBufferRef = useRef<string>('');
    const updateTimerRef = useRef<NodeJS.Timeout | null>(null);

    // 获取当前章节内容
    const currentContent = selectedChapterId ? (state.generatedContent[selectedChapterId] || '') : '';

    // 递归获取所有章节选项
    const getAllChapters = (outline: any[], level = 0): { value: string; label: string }[] => {
        let chapters: { value: string; label: string }[] = [];
        outline.forEach((item) => {
            const prefix = '\u00A0\u00A0'.repeat(level * 2);
            chapters.push({ 
                value: item.id, 
                label: `${prefix}${item.id} ${item.title}` 
            });
            
            if (item.children) {
                chapters = chapters.concat(getAllChapters(item.children, level + 1));
            }
        });
        return chapters;
    };

    const chapterOptions = getAllChapters(state.outline);

    // 自动选择第一个有内容的章节
    useEffect(() => {
        if (!selectedChapterId && chapterOptions.length > 0) {
            const firstGenerated = chapterOptions.find(opt => state.generatedContent[opt.value]);
            if (firstGenerated) {
                setSelectedChapterId(firstGenerated.value);
            } else {
                setSelectedChapterId(chapterOptions[0].value);
            }
        }
    }, [state.generatedContent, chapterOptions, selectedChapterId]);

    // 🟢 核心修复2：清理定时器
    useEffect(() => {
        return () => {
            if (updateTimerRef.current) {
                clearTimeout(updateTimerRef.current);
            }
        };
    }, []);

    // 处理内容变更
    const handleContentChange = (content: string) => {
        if (selectedChapterId) {
            setState((prev) => ({
                ...prev,
                generatedContent: {
                    ...prev.generatedContent,
                    [selectedChapterId]: content
                }
            }));
        }
    };

    // 🟢 辅助函数：查找当前章节对象及其父级链
    const findChapterInfo = (items: OutlineItem[], targetId: string, parents: OutlineItem[] = []): { node: OutlineItem, parents: OutlineItem[] } | null => {
        for (const item of items) {
            if (item.id === targetId) return { node: item, parents };
            if (item.children) {
                const found = findChapterInfo(item.children, targetId, [...parents, item]);
                if (found) return found;
            }
        }
        return null;
    };

    // 🟢 点击"AI 重写本章"按钮
    const handleRegenerateClick = () => {
        if (!selectedChapterId) return;
        setRegenPrompt('');
        setIsRegenModalOpen(true);
    };

    // 🟢 核心修复3：优化的确认重写函数
    const handleRegenerateConfirm = async () => {
        if (!selectedChapterId) return;
        
        const chapterInfo = findChapterInfo(state.outline, selectedChapterId);
        if (!chapterInfo) {
            message.error("未找到章节信息");
            return;
        }

        setIsRegenerating(true);
        
        // 初始化流式缓冲区
        streamBufferRef.current = '';
        
        // 清空当前内容
        setState(prev => ({
            ...prev,
            generatedContent: { ...prev.generatedContent, [selectedChapterId]: '' }
        }));

        try {
            await regenerateSingleChapter(
                chapterInfo.node,
                chapterInfo.parents,
                state.overview,
                state.requirements,
                regenPrompt,
                currentContent,
                state.config,
                (chunk) => {
                    // ✅ 核心修复：使用防抖策略批量更新
                    streamBufferRef.current += chunk;
                    
                    // 清除之前的定时器
                    if (updateTimerRef.current) {
                        clearTimeout(updateTimerRef.current);
                    }
                    
                    // 设置新的定时器：100ms内的所有chunk会被合并成一次更新
                    updateTimerRef.current = setTimeout(() => {
                        const bufferedContent = streamBufferRef.current;
                        setState(prev => ({
                            ...prev,
                            generatedContent: { 
                                ...prev.generatedContent, 
                                [selectedChapterId]: bufferedContent
                            }
                        }));
                    }, 100); // 100ms防抖
                }
            );
            
            // ✅ 生成完成后，立即刷新最终内容（避免最后一段被延迟）
            if (updateTimerRef.current) {
                clearTimeout(updateTimerRef.current);
            }
            const finalContent = streamBufferRef.current;
            setState(prev => ({
                ...prev,
                generatedContent: { 
                    ...prev.generatedContent, 
                    [selectedChapterId]: finalContent
                }
            }));
            
            message.success("重写完成");
            setIsRegenModalOpen(false);
        } catch (error) {
            console.error(error);
            message.error("重写失败，请重试");
        } finally {
            setIsRegenerating(false);
            streamBufferRef.current = ''; // 清空缓冲区
        }
    };

    // 🟢 新增：处理"进入数据库管理"或"完成编辑"点击
    const handleDatabaseManagement = () => {
        message.info('已保存当前编辑内容。您可以从"知识与数据管理"页面进行高级查询。', 5);
        onNext(); 
    };

    const handleRegenerateChapter = () => {
        message.info("重新生成功能需连接后端流式接口，当前仅演示编辑功能");
    };

    // 🟢 新增：单独的导出功能
    const handleOneClickExport = async () => {
         setLoading(true);
        try {
            message.info('正在打包导出 Word 文档...');
            await exportToWord(state.generatedContent, state.outline);
            message.success('导出成功！');
        } catch (error) {
            message.error('导出失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AntdLayout className="editor-layout">
            <style>{editorStyles}</style>
            
            <div style={{ background: '#fff', padding: '12px 24px', borderBottom: '1px solid #e8e8e8', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', zIndex: 200 }}>
                <Space size="middle">
                    <Title level={4} style={{ margin: 0, color: '#1890ff' }}><EditOutlined /> 内容精修</Title>
                    <span style={{ color: '#e8e8e8' }}>|</span>
                    {state.isGenerating || isRegenerating ? (
                        <Tag icon={<LoadingOutlined />} color="processing">AI 正在撰写中...</Tag>
                    ) : (
                        <Tag icon={<CheckCircleOutlined />} color="success">就绪</Tag>
                    )}
                    <Text>当前章节：</Text>
                    <Select
                        style={{ width: 400 }} 
                        placeholder="切换章节"
                        options={chapterOptions}
                        value={selectedChapterId}
                        onChange={setSelectedChapterId}
                        showSearch
                        filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
                    />
                </Space>

                <Space>
                    <Button 
                        icon={<ReloadOutlined />} 
                        onClick={handleRegenerateClick}
                        disabled={!selectedChapterId || isRegenerating}
                        loading={isRegenerating}
                    >
                        AI 重写本章
                    </Button>
                    <Button type="primary" icon={<DatabaseOutlined />} onClick={handleDatabaseManagement} disabled={Object.keys(state.generatedContent).length === 0}>
                        转到数据管理
                    </Button>
                    <Button icon={<FileWordOutlined />} onClick={handleOneClickExport} loading={loading} disabled={Object.keys(state.generatedContent).length === 0}>
                        导出 Word
                    </Button>
                </Space>
            </div>

            <Content style={{ padding: '24px', overflowY: 'auto' }}>
                <Spin spinning={loading || isRegenerating} tip="AI 奋笔疾书中...">
                    {selectedChapterId ? (
                        <div className="a4-paper-container">
                            <QuillWrapper
                                theme="snow"
                                value={currentContent}
                                onChange={handleContentChange}
                                modules={modules}
                                formats={formats}
                                className="quill-editor"
                                placeholder="此处将显示 AI 生成的内容..."
                            />
                        </div>
                    ) : (
                        <div style={{ marginTop: 100 }}><Empty description="请先在左上角选择一个章节" /></div>
                    )}
                </Spin>
            </Content>

            {/* 🟢 重写交互弹窗 */}
            <Modal
                title="AI 章节重写"
                open={isRegenModalOpen}
                onOk={handleRegenerateConfirm}
                onCancel={() => setIsRegenModalOpen(false)}
                okText="开始重写"
                cancelText="取消"
                confirmLoading={isRegenerating}
            >
                <div style={{ marginBottom: 16 }}>
                    <Text>请输入您的修改建议（留空则自动重新生成）：</Text>
                </div>
                <TextArea 
                    rows={4} 
                    placeholder="例如：请增加关于数据安全保护的具体措施；语气更正式一些..." 
                    value={regenPrompt}
                    onChange={(e) => setRegenPrompt(e.target.value)}
                />
                <div style={{ marginTop: 16, color: '#888', fontSize: '12px' }}>
                    * AI 将参考原有内容和您的建议进行修改。
                </div>
            </Modal>
        </AntdLayout>
    );
};

export default ContentEdit;