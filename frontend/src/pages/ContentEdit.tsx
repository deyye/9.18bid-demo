import React, { useState } from 'react';
import { Button, Card, Select, message, Spin, Typography, Layout as AntdLayout, Tooltip } from 'antd';
import useAppState from '../hooks/useAppState';
import { generateContent, exportToWord } from '../services/api';
import { FileWordOutlined, ReloadOutlined } from '@ant-design/icons';
// 假设引入了一个轻量级的富文本编辑器，这里使用TextArea模拟，并应用A4样式

const { Title, Paragraph } = Typography;
const { Content } = AntdLayout;

interface ContentEditProps {
    onNext: () => void;
}

const ContentEdit: React.FC<ContentEditProps> = ({ onNext }) => {
    const { state, setState } = useAppState();
    const [loading, setLoading] = useState(false);
    const [selectedChapterId, setSelectedChapterId] = useState<string | undefined>(undefined);
    
    // 假设当前编辑的内容是 state.generatedContent[selectedChapterId]
    const currentContent = selectedChapterId ? state.generatedContent[selectedChapterId] : '';

    // 优化点 2: 模拟富文本编辑器的内容更新
    const handleContentChange = (newContent: string) => {
        if (selectedChapterId) {
            setState({ 
                generatedContent: { 
                    ...state.generatedContent, 
                    [selectedChapterId]: newContent 
                } 
            });
        }
    };

    // 递归获取所有章节选项
    const getAllChapters = (outline: any[], level = 0): { value: string; label: string }[] => {
        let chapters: { value: string; label: string }[] = [];
        outline.forEach((item) => {
            const prefix = '— '.repeat(level);
            chapters.push({ value: item.id, label: `${prefix}${item.title}` });
            if (item.children) {
                chapters = chapters.concat(getAllChapters(item.children, level + 1));
            }
        });
        return chapters;
    };

    const chapterOptions = getAllChapters(state.outline);

    // 模拟重新生成当前章节内容
    const handleRegenerateChapter = async () => {
        if (!selectedChapterId) {
            message.warning('请先选择一个章节进行内容生成。');
            return;
        }
        setLoading(true);
        try {
            message.info(`正在重新生成 ${selectedChapterId} 的内容...`);
            // 实际调用 API 重新生成单个章节
            // const result = await regenerateChapter(selectedChapterId, state.outline, state.config);
            // setState({ generatedContent: { ...state.generatedContent, [selectedChapterId]: result } });
            // 模拟结果
            setTimeout(() => {
                const newContent = `【AI重新生成内容】这是针对章节 ${selectedChapterId} 的全新、高质量内容，已基于您的字数设定（${state.outline.find(i => i.id === selectedChapterId)?.wordCount || '未设置'}字）进行了优化。您可以进行实时修改。`;
                 setState({ 
                    generatedContent: { 
                        ...state.generatedContent, 
                        [selectedChapterId]: newContent 
                    } 
                });
                message.success('章节内容重新生成成功！');
                setLoading(false);
            }, 1500);
            
        } catch (error) {
            message.error('章节内容重新生成失败。');
        } finally {
            // setLoading(false); // 在 setTimeout 中处理
        }
    };
    
    // 导出 Word 文档
    const handleExport = async () => {
        setLoading(true);
        try {
            message.info('正在请求后端生成 Word 文档，请稍候...');
            await exportToWord(state.generatedContent, state.outline);
            message.success('Word 文档导出成功！');
            onNext(); // 跳转到导出完成步骤
        } catch (error) {
            message.error('Word 文档导出失败。');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AntdLayout style={{ background: '#f5f5f5' }}>
            {/* 顶部的章节选择和操作栏 */}
            <Content style={{ marginBottom: 16, padding: 16, background: '#fff', borderRadius: 8 }}>
                <Title level={5} style={{ margin: 0 }}>选择章节编辑</Title>
                <Select
                    style={{ width: '100%', marginTop: 8 }}
                    placeholder="请选择要查看和编辑的章节"
                    options={chapterOptions}
                    value={selectedChapterId}
                    onChange={setSelectedChapterId}
                    showSearch
                />
                <div style={{ marginTop: 16, textAlign: 'right' }}>
                     <Button 
                        icon={<ReloadOutlined />}
                        onClick={handleRegenerateChapter}
                        disabled={!selectedChapterId || loading}
                        style={{ marginRight: 8 }}
                    >
                        重新生成当前章节
                    </Button>
                    <Button 
                        icon={<FileWordOutlined />}
                        onClick={handleExport}
                        type="primary"
                        disabled={Object.keys(state.generatedContent).length === 0 || loading}
                    >
                        一键导出 Word
                    </Button>
                </div>
            </Content>

            {/* 优化点 2: 类似 Word 的布局实时修改 */}
            <div className="editor-wrapper">
                <Spin spinning={loading} tip="内容正在生成/更新...">
                    <div className="word-paper">
                        <Title level={2} style={{ textAlign: 'center', marginTop: 0 }}>
                            {selectedChapterId ? chapterOptions.find(o => o.value === selectedChapterId)?.label : '标书内容编辑区'}
                        </Title>
                        
                        {!selectedChapterId && <Paragraph type="secondary" style={{ textAlign: 'center', marginTop: 50 }}>请在上方选择一个章节开始编辑。</Paragraph>}

                        {/* 这是一个简化的实时编辑区，实际应替换为 TipTap/Slate 等富文本编辑器 */}
                        {selectedChapterId && (
                            <div
                                contentEditable={true} // 启用实时编辑
                                onInput={(e: React.FormEvent<HTMLDivElement>) => handleContentChange(e.currentTarget.innerHTML)}
                                dangerouslySetInnerHTML={{ __html: currentContent || 'AI 内容生成中...' }}
                                style={{
                                    minHeight: '800px', 
                                    padding: '10px',
                                    border: '1px solid #ccc',
                                    backgroundColor: '#fafafa',
                                    outline: 'none',
                                    marginTop: 20,
                                    // 模拟富文本样式
                                    lineHeight: 1.6,
                                    fontSize: '14px'
                                }}
                            />
                        )}
                        
                    </div>
                </Spin>
            </div>
        </AntdLayout>
    );
};

export default ContentEdit;