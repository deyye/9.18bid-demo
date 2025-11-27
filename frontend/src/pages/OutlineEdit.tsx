import React, { useState } from 'react';
import { Button, Card, Tree, InputNumber, Space, Typography, message, Spin } from 'antd';
import { OutlineItem, ProcessStep } from '../types';
import useAppState from '../hooks/useAppState';
import { generateOutline, generateContent } from '../services/api'; 

const { Title, Text } = Typography;

interface OutlineEditProps {
    onNext: () => void;
}

const OutlineEdit: React.FC<OutlineEditProps> = ({ onNext }) => {
    const { state, setState } = useAppState();
    const [loading, setLoading] = useState(false);
    
    // -------------------------------------------------------------------------
    // 1. 辅助函数定义 (这些函数必须存在，否则 Tree 无法渲染)
    // -------------------------------------------------------------------------

    // 递归查找并更新字数
    const updateWordCountRecursively = (items: OutlineItem[], id: string, wordCount: number | null): OutlineItem[] => {
        return items.map(item => {
            if (item.id === id) {
                // 如果 wordCount 为 null 或 0，则设置为 undefined
                return { ...item, wordCount: (wordCount === null || wordCount === 0) ? undefined : wordCount };
            }
            if (item.children) {
                return { ...item, children: updateWordCountRecursively(item.children, id, wordCount) };
            }
            return item;
        });
    };

    // 处理字数变化 (本地状态更新)
    const handleWordCountChange = (id: string, value: number | null) => {
        const newOutline = updateWordCountRecursively(state.outline, id, value);
        setState({ outline: newOutline });
    };

    // 转换 OutlineItem[] 为 Ant Design Tree Data (需要 title, key, children)
    const outlineToTreeData = (outline: OutlineItem[]): any[] => {
        return outline.map(item => ({
            key: item.id,
            // 确保只有 Level 2 和 Level 3 的章节可以设置字数
            title: (
                <Space>
                    <Text strong style={{ minWidth: 200 }}>{item.title}</Text>
                    {/* 优化点: 字数设置 InputNumber */}
                    {item.level >= 2 && (
                        <InputNumber
                            min={100}
                            placeholder="目标字数"
                            value={item.wordCount}
                            // 确保 onChange 传入 number | null
                            onChange={(value) => handleWordCountChange(item.id, value as number | null)} 
                            addonAfter="字"
                            style={{ width: 140 }}
                            step={100}
                        />
                    )}
                </Space>
            ),
            isLeaf: !item.children || item.children.length === 0,
            children: item.children ? outlineToTreeData(item.children) : undefined,
        }));
    };

    // -------------------------------------------------------------------------
    // 2. 业务逻辑函数 (已适配新的 overview/requirements 参数)
    // -------------------------------------------------------------------------

    // 模拟 AI 生成目录
    const handleGenerateOutline = async () => {
        // 检查必要字段是否存在
        if (!state.documentContent || !state.overview || !state.requirements) {
            message.error('请先完成文档分析步骤（需包含项目概述和技术要求）！');
            return;
        }

        setLoading(true);
        try {
            // 调用 API，传入新的参数
            const result = await generateOutline(state.overview, state.requirements, state.config);
            
            setState({ 
                outline: result, 
                currentStep: ProcessStep.OUTLINE_EDIT // 保持在当前步骤
            });
            message.success('AI 目录生成成功！请调整字数后开始内容生成。');
        } catch (error: any) {
            console.error(error);
            message.error('AI 目录生成失败，请检查后端服务。');
        } finally {
            setLoading(false);
        }
    };

    // 开始内容生成
    const handleGenerateContent = async () => {
        if (state.outline.length === 0) {
             message.warning('目录为空，无法生成内容。请先生成目录。');
             return;
        }
        setLoading(true);
        try {
            message.info('开始内容生成，这可能需要一些时间...');
            
            // 调用 API，传递 overview 和 requirements
            const result = await generateContent(
                state.documentContent, 
                state.overview, 
                state.requirements, 
                state.outline, 
                state.config
            );
            
            setState({ generatedContent: result });
            onNext(); // 跳转到内容编辑页面
        } catch (error: any) {
            console.error(error);
            message.error('内容生成失败。');
        } finally {
            setLoading(false);
        }
    };

    // -------------------------------------------------------------------------
    // 3. 渲染
    // -------------------------------------------------------------------------

    return (
        <Card title="AI生成目录与字数设定" style={{ minHeight: '80vh' }}>
            <Spin spinning={loading} tip="AI正在工作...">
                <Space style={{ marginBottom: 16 }}>
                    <Button onClick={handleGenerateOutline} disabled={!state.overview || loading} type="primary">
                        重新生成目录
                    </Button>
                    <Button onClick={handleGenerateContent} disabled={state.outline.length === 0 || loading} type="primary" danger>
                        开始内容生成
                    </Button>
                </Space>

                <Title level={4}>标书目录结构（拖拽调整 & 设置字数）</Title>
                
                {state.outline.length === 0 ? (
                    <Text type="secondary">请先解析招标文件并生成目录。</Text>
                ) : (
                    // 使用 Ant Design Tree 渲染
                    <div style={{ maxHeight: '60vh', overflowY: 'auto', border: '1px solid #f0f0f0', padding: 10 }}>
                        <Tree
                            showLine={true}
                            defaultExpandAll={true}
                            treeData={outlineToTreeData(state.outline)} // ✅ 现在可以找到这个函数了
                        />
                    </div>
                )}
            </Spin>
        </Card>
    );
};

export default OutlineEdit;