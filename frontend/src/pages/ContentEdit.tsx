import React, { useState, useEffect } from 'react';
import { Button, Select, message, Spin, Typography, Layout as AntdLayout, Space, Empty } from 'antd';
import { FileWordOutlined, ReloadOutlined, EditOutlined } from '@ant-design/icons';
import useAppState from '../hooks/useAppState';
import { exportToWord } from '../services/api';
// 引入 ReactQuill 及样式
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';

// 🟢 关键修复：创建一个避开类型检查的 Quill 包装器
// 这里使用 'as any' 彻底解决 "JSX element class does not support attributes" 报错
const QuillWrapper = ReactQuill as any;

const { Title, Text } = Typography;
const { Content } = AntdLayout;

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
        ['bold', 'italic', 'underline', 'strike'],        // 字体样式
        [{ 'color': [] }, { 'background': [] }],          // 颜色
        [{ 'list': 'ordered'}, { 'list': 'bullet' }],     // 列表
        [{ 'indent': '-1'}, { 'indent': '+1' }],          // 缩进
        [{ 'align': [] }],                                // 对齐
        ['clean']                                         // 清除格式
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
    
    // 获取当前章节内容（如果没有则为空字符串）
    const currentContent = selectedChapterId ? (state.generatedContent[selectedChapterId] || '') : '';

    // 递归获取所有章节选项
    const getAllChapters = (outline: any[], level = 0): { value: string; label: string }[] => {
        let chapters: { value: string; label: string }[] = [];
        outline.forEach((item) => {
            const prefix = '\u00A0\u00A0'.repeat(level * 2); // 使用空格缩进显示层级
            chapters.push({ value: item.id, label: `${prefix}${item.title}` });
            if (item.children) {
                chapters = chapters.concat(getAllChapters(item.children, level + 1));
            }
        });
        return chapters;
    };

    const chapterOptions = getAllChapters(state.outline);

    // 自动选择第一个有内容的章节（如果未选择）
    useEffect(() => {
        if (!selectedChapterId && chapterOptions.length > 0) {
            // 优先找已经生成了内容的章节
            const firstGenerated = chapterOptions.find(opt => state.generatedContent[opt.value]);
            if (firstGenerated) {
                setSelectedChapterId(firstGenerated.value);
            } else {
                setSelectedChapterId(chapterOptions[0].value);
            }
        }
    }, [state.generatedContent, selectedChapterId, chapterOptions]);

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

    // 导出 Word
    const handleExport = async () => {
        setLoading(true);
        try {
            message.info('正在打包导出 Word 文档...');
            await exportToWord(state.generatedContent, state.outline);
            message.success('导出成功！');
            onNext();
        } catch (error) {
            message.error('导出失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    // 模拟重新生成（这里依然保留接口，但主要展示编辑功能）
    const handleRegenerateChapter = () => {
        message.info("重新生成功能需连接后端流式接口，当前仅演示编辑功能");
    };

    return (
        <AntdLayout className="editor-layout">
            <style>{editorStyles}</style>
            
            {/* 顶部操作栏 */}
            <div style={{ 
                background: '#fff', 
                padding: '12px 24px', 
                borderBottom: '1px solid #e8e8e8',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                zIndex: 200
            }}>
                <Space size="middle">
                    <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
                        <EditOutlined /> 内容精修
                    </Title>
                    <span style={{ color: '#e8e8e8' }}>|</span>
                    <Text>当前章节：</Text>
                    <Select
                        style={{ width: 300 }}
                        placeholder="切换章节"
                        options={chapterOptions}
                        value={selectedChapterId}
                        onChange={setSelectedChapterId}
                        showSearch
                        filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                        }
                    />
                </Space>

                <Space>
                    <Button 
                        icon={<ReloadOutlined />} 
                        onClick={handleRegenerateChapter}
                        disabled={!selectedChapterId}
                    >
                        AI 重写本章
                    </Button>
                    <Button 
                        type="primary" 
                        icon={<FileWordOutlined />} 
                        onClick={handleExport}
                        loading={loading}
                        disabled={Object.keys(state.generatedContent).length === 0}
                    >
                        导出完整标书
                    </Button>
                </Space>
            </div>

            {/* 编辑区主体 */}
            <Content style={{ padding: '24px', overflowY: 'auto' }}>
                <Spin spinning={loading}>
                    {selectedChapterId ? (
                        <div className="a4-paper-container">
                            {/* ✅ 修正点：这里必须使用 QuillWrapper，不能用 ReactQuill */}
                            <QuillWrapper
                                theme="snow"
                                value={currentContent}
                                onChange={handleContentChange}
                                modules={modules}
                                formats={formats}
                                className="quill-editor"
                                placeholder="此处将显示 AI 生成的内容，您可以像使用 Word 一样直接编辑..."
                            />
                        </div>
                    ) : (
                        <div style={{ marginTop: 100 }}>
                            <Empty description="请先在左上角选择一个章节" />
                        </div>
                    )}
                </Spin>
            </Content>
        </AntdLayout>
    );
};

export default ContentEdit;