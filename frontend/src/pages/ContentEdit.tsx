import React, { useState, useEffect, useMemo } from 'react';
import { Button, Select, message, Spin, Typography, Layout as AntdLayout, Space, Empty, Tag, Tooltip } from 'antd';
import { FileWordOutlined, ReloadOutlined, EditOutlined, LoadingOutlined, CheckCircleOutlined, FormatPainterOutlined } from '@ant-design/icons';
import useAppState from '../hooks/useAppState';
import { exportToWord } from '../services/api';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
// ✅ 引入 marked 进行 Markdown -> HTML 转换
import { marked } from 'marked';

// 解决 TS 类型报错
const QuillWrapper = ReactQuill as any;

const { Title, Text } = Typography;
const { Content } = AntdLayout;

interface ContentEditProps {
    onNext: () => void;
}

// ... (样式 editorStyles 和 modules, formats 保持不变，请保留你原有的代码)
const editorStyles = `
    /* 整体背景 */
    .editor-layout {
        background-color: #f0f2f5;
        min-height: 100vh;
    }
    .a4-paper-container {
        width: 210mm;
        min-height: 297mm;
        margin: 24px auto;
        background: white;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        padding: 0;
        position: relative;
        display: flex;
        flex-direction: column;
    }
    .quill-editor { flex: 1; display: flex; flex-direction: column; }
    .ql-toolbar.ql-snow {
        position: sticky; top: 0; z-index: 100; background: #f8f9fa;
        border: none !important; border-bottom: 1px solid #ddd !important;
        padding: 12px 8px !important; text-align: center;
    }
    .ql-container.ql-snow { border: none !important; flex: 1; font-family: 'Songti SC', 'SimSun', serif; font-size: 16px; }
    .ql-editor { padding: 25.4mm 31.8mm; line-height: 1.8; min-height: 250mm; }
    .ql-editor h1 { font-size: 24px; font-weight: bold; margin-bottom: 16px; }
    .ql-editor h2 { font-size: 20px; font-weight: bold; margin-top: 12px; margin-bottom: 12px; }
    .ql-editor h3 { font-size: 18px; font-weight: bold; }
    .ql-editor p { margin-bottom: 8px; text-indent: 2em; } /* 首行缩进 */
`;

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
    'header', 'bold', 'italic', 'underline', 'strike', 'color', 'background', 'list', 'bullet', 'indent', 'align'
];

const ContentEdit: React.FC<ContentEditProps> = ({ onNext }) => {
    const { state, setState } = useAppState();
    const [loading, setLoading] = useState(false);
    const [selectedChapterId, setSelectedChapterId] = useState<string | undefined>(undefined);
    
    // 获取当前章节的原始内容（可能是 Markdown 或 HTML）
    const rawContent = selectedChapterId ? (state.generatedContent[selectedChapterId] || '') : '';

    // ✅ 智能转换：如果是 Markdown 格式，自动转为 HTML，否则保持原样
    // 简单的启发式判断：如果包含 HTML 标签则认为是 HTML，否则认为是 Markdown
    const displayContent = useMemo(() => {
        if (!rawContent) return '';
        const isHtml = /<[a-z][\s\S]*>/i.test(rawContent);
        if (isHtml) return rawContent;
        
        // 使用 marked 转换 Markdown -> HTML
        try {
            return marked.parse(rawContent);
        } catch (e) {
            return rawContent;
        }
    }, [rawContent]);

    const getAllChapters = (outline: any[], level = 0): { value: string; label: string }[] => {
        let chapters: { value: string; label: string }[] = [];
        outline.forEach((item) => {
            const prefix = '\u00A0\u00A0'.repeat(level * 2);
            chapters.push({ value: item.id, label: `${prefix}${item.title}` });
            if (item.children) {
                chapters = chapters.concat(getAllChapters(item.children, level + 1));
            }
        });
        return chapters;
    };

    const chapterOptions = getAllChapters(state.outline);

    useEffect(() => {
        if (!selectedChapterId && chapterOptions.length > 0) {
            const firstGenerated = chapterOptions.find(opt => state.generatedContent[opt.value]);
            if (firstGenerated) {
                setSelectedChapterId(firstGenerated.value);
            } else {
                setSelectedChapterId(chapterOptions[0].value);
            }
        }
    }, [state.generatedContent]);

    const handleContentChange = (content: string) => {
        if (selectedChapterId) {
            setState((prev) => ({
                ...prev,
                generatedContent: {
                    ...prev.generatedContent,
                    [selectedChapterId]: content // 保存的是编辑器产生的 HTML
                }
            }));
        }
    };

    const handleExport = async () => {
        setLoading(true);
        try {
            message.info('正在智能排版并导出 Word 文档...');
            await exportToWord(state.generatedContent, state.outline);
            message.success('导出成功！');
            onNext();
        } catch (error) {
            message.error('导出失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    // 🌟 新增：一键排版优化（中英文加空格等）
    const handleSmartFormat = () => {
        if (!displayContent) return;
        // 简单的排版规则：中英文之间加空格
        // 注意：这只是对纯文本处理，在 HTML 中直接正则替换有风险，这里仅做简单示例
        // 实际项目建议在后端处理或使用更复杂的 DOM 遍历
        message.success("已应用智能排版规则（模拟）");
    };

    const handleRegenerateChapter = () => {
        message.info("重新生成功能需连接后端流式接口");
    };

    return (
        <AntdLayout className="editor-layout">
            <style>{editorStyles}</style>
            
            <div style={{ 
                background: '#fff', padding: '12px 24px', borderBottom: '1px solid #e8e8e8',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)', zIndex: 200
            }}>
                <Space size="middle">
                    <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
                        <EditOutlined /> 内容精修
                    </Title>
                    <span style={{ color: '#e8e8e8' }}>|</span>
                    
                    {state.isGenerating ? (
                        <Tag icon={<LoadingOutlined />} color="processing">
                            AI 正在撰写中... ({Object.keys(state.generatedContent).length}/{chapterOptions.length})
                        </Tag>
                    ) : (
                        <Tag icon={<CheckCircleOutlined />} color="success">生成完成</Tag>
                    )}

                    <Text>当前章节：</Text>
                    <Select
                        style={{ width: 300 }}
                        placeholder="切换章节"
                        options={chapterOptions}
                        value={selectedChapterId}
                        onChange={setSelectedChapterId}
                        showSearch
                        filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
                    />
                </Space>

                <Space>
                    <Tooltip title="一键优化排版（中英文空格等）">
                        <Button icon={<FormatPainterOutlined />} onClick={handleSmartFormat}>优化排版</Button>
                    </Tooltip>
                    <Button icon={<ReloadOutlined />} onClick={handleRegenerateChapter} disabled={!selectedChapterId}>
                        AI 重写
                    </Button>
                    <Button type="primary" icon={<FileWordOutlined />} onClick={handleExport} loading={loading} disabled={Object.keys(state.generatedContent).length === 0}>
                        导出完整标书
                    </Button>
                </Space>
            </div>

            <Content style={{ padding: '24px', overflowY: 'auto' }}>
                <Spin spinning={loading}>
                    {selectedChapterId ? (
                        <div className="a4-paper-container">
                            <QuillWrapper
                                theme="snow"
                                value={displayContent} // 使用转换后的 HTML
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
        </AntdLayout>
    );
};

export default ContentEdit;