import React, { useState } from 'react';
import { Button, Card, Tree, InputNumber, Space, Typography, message, Spin, Modal, Input, Tooltip, Popconfirm, Tag, Empty, Row, Col } from 'antd';
import { 
    EditOutlined, 
    PlusOutlined, 
    DeleteOutlined, 
    FileTextOutlined, 
    SaveOutlined, 
    FolderOpenOutlined, 
    FileOutlined,
    AimOutlined,
    CalculatorOutlined
} from '@ant-design/icons';
// 引入 AppState 以修复类型报错
import { OutlineItem, ProcessStep, AppState } from '../types';
import useAppState from '../hooks/useAppState';
import { generateOutline, generateContentStream } from '../services/api'; 
import type { DataNode, TreeProps } from 'antd/es/tree';

// 样式：确保树节点占满整行，对齐美观
const treeStyles = `
  .ant-tree-node-content-wrapper {
    display: flex;
    width: 100%;
    padding: 0 !important;
  }
  .ant-tree-title {
    width: 100%;
  }
  .custom-tree-node {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 8px 12px;
    border-bottom: 1px dashed #f0f0f0;
    transition: background-color 0.3s;
  }
  .custom-tree-node:hover {
    background-color: #fafafa;
  }
  .ant-tree-switcher-noop {
    display: none !important;
  }
`;

const { Title, Text } = Typography;

interface OutlineEditProps {
    onNext: () => void;
}

const OutlineEdit: React.FC<OutlineEditProps> = ({ onNext }) => {
    const { state, setState } = useAppState();
    const [loading, setLoading] = useState(false); // 仅用于目录生成的 loading
    
    // 全文总字数状态
    const [totalTargetWords, setTotalTargetWords] = useState<number>(5000);

    // --- 弹窗状态管理 ---
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalMode, setModalMode] = useState<'edit' | 'add'>('add');
    const [currentEditNode, setCurrentEditNode] = useState<OutlineItem | null>(null);
    const [modalInputValue, setModalInputValue] = useState('');

    // -------------------------------------------------------------------------
    // 1. 核心数据操作辅助函数
    // -------------------------------------------------------------------------

    // 递归查找并更新字数
    const updateWordCountRecursively = (items: OutlineItem[], id: string, wordCount: number | null): OutlineItem[] => {
        return items.map(item => {
            if (item.id === id) {
                return { ...item, wordCount: (wordCount === null || wordCount === 0) ? undefined : wordCount };
            }
            if (item.children) {
                return { ...item, children: updateWordCountRecursively(item.children, id, wordCount) };
            }
            return item;
        });
    };

    // 统计所有叶子节点（最底层的章节，即需要写内容的章节）
    const countLeafNodes = (items: OutlineItem[]): number => {
        let count = 0;
        items.forEach(item => {
            if (!item.children || item.children.length === 0) {
                count++;
            } else {
                count += countLeafNodes(item.children);
            }
        });
        return count;
    };

    // 递归给所有叶子节点分配字数
    const distributeWordCountRecursively = (items: OutlineItem[], countPerNode: number): OutlineItem[] => {
        return items.map(item => {
            // 如果是叶子节点，设置字数
            if (!item.children || item.children.length === 0) {
                return { ...item, wordCount: countPerNode };
            }
            // 如果有子节点，继续递归
            return { ...item, children: distributeWordCountRecursively(item.children, countPerNode) };
        });
    };

    // -------------------------------------------------------------------------
    // 2. 事件处理器
    // -------------------------------------------------------------------------

    // 处理“一键分配”
    const handleDistributeWords = () => {
        if (!totalTargetWords || totalTargetWords <= 0) {
            message.warning('请输入有效的总字数');
            return;
        }

        const leafCount = countLeafNodes(state.outline);
        if (leafCount === 0) {
            message.warning('当前没有可分配的章节');
            return;
        }

        // 向下取整，分配给每个章节
        const perNodeCount = Math.floor(totalTargetWords / leafCount);
        
        // 更新整个树
        const newOutline = distributeWordCountRecursively(state.outline, perNodeCount);
        setState({ outline: newOutline });
        
        message.success(`已将 ${totalTargetWords} 字平均分配给 ${leafCount} 个章节（每章约 ${perNodeCount} 字）`);
    };

    const handleWordCountChange = (id: string, value: number | null) => {
        const newOutline = updateWordCountRecursively(state.outline, id, value);
        setState({ outline: newOutline });
    };

    // ... (增删改查弹窗逻辑)
    const updateTitleRecursively = (items: OutlineItem[], id: string, newTitle: string): OutlineItem[] => {
        return items.map(item => {
            if (item.id === id) return { ...item, title: newTitle };
            if (item.children) return { ...item, children: updateTitleRecursively(item.children, id, newTitle) };
            return item;
        });
    };
    const addChildRecursively = (items: OutlineItem[], parentId: string, newItem: OutlineItem): OutlineItem[] => {
        return items.map(item => {
            if (item.id === parentId) {
                const children = item.children || [];
                return { ...item, children: [...children, newItem] };
            }
            if (item.children) return { ...item, children: addChildRecursively(item.children, parentId, newItem) };
            return item;
        });
    };
    const deleteNodeRecursively = (items: OutlineItem[], id: string): OutlineItem[] => {
        return items.filter(item => item.id !== id).map(item => {
            if (item.children) return { ...item, children: deleteNodeRecursively(item.children, id) };
            return item;
        });
    };
    const openModal = (mode: 'edit' | 'add', node: OutlineItem) => {
        setModalMode(mode);
        setCurrentEditNode(node);
        setModalInputValue(mode === 'edit' ? node.title : '');
        setIsModalOpen(true);
    };
    const handleModalOk = () => {
        if (!modalInputValue.trim()) { message.warning("内容不能为空"); return; }
        if (modalMode === 'edit' && currentEditNode) {
            const newOutline = updateTitleRecursively(state.outline, currentEditNode.id, modalInputValue);
            setState({ outline: newOutline });
            message.success("修改成功");
        } else if (modalMode === 'add' && currentEditNode) {
            const newItem: OutlineItem = {
                id: `${currentEditNode.id}-${Date.now()}`,
                title: modalInputValue,
                level: currentEditNode.level + 1,
                children: []
            };
            const newOutline = addChildRecursively(state.outline, currentEditNode.id, newItem);
            setState({ outline: newOutline });
            message.success("添加成功");
        }
        setIsModalOpen(false);
    };
    const handleDeleteNode = (id: string) => {
        const newOutline = deleteNodeRecursively(state.outline, id);
        setState({ outline: newOutline });
        message.success("删除成功");
    };

    // -------------------------------------------------------------------------
    // 3. 拖拽逻辑
    // -------------------------------------------------------------------------
    const onDrop: TreeProps['onDrop'] = (info) => {
        const dropKey = info.node.key as string;
        const dragKey = info.dragNode.key as string;
        const dropPos = info.node.pos.split('-');
        const dropPosition = info.dropPosition - Number(dropPos[dropPos.length - 1]);
        const data = [...state.outline];
        const loop = (data: OutlineItem[], key: string, callback: (item: OutlineItem, index: number, arr: OutlineItem[]) => void) => {
            for (let i = 0; i < data.length; i++) {
                if (data[i].id === key) return callback(data[i], i, data);
                if (data[i].children) loop(data[i].children!, key, callback);
            }
        };
        let dragObj: OutlineItem;
        loop(data, dragKey, (item, index, arr) => { arr.splice(index, 1); dragObj = item; });
        if (!info.dropToGap) {
            loop(data, dropKey, (item) => { item.children = item.children || []; dragObj.level = item.level + 1; item.children.push(dragObj); });
        } else if ((info.node.children || []).length > 0 && info.node.expanded && dropPosition === 1) {
            loop(data, dropKey, (item) => { item.children = item.children || []; dragObj.level = item.level + 1; item.children.unshift(dragObj); });
        } else {
            let ar: OutlineItem[] = [];
            let i: number = 0;
            loop(data, dropKey, (_item, index, arr) => { ar = arr; i = index; });
            if (dropPosition === -1) { ar.splice(i, 0, dragObj!); } else { ar.splice(i + 1, 0, dragObj!); }
        }
        setState({ outline: data });
    };

    // -------------------------------------------------------------------------
    // 4. Tree 渲染数据转换
    // -------------------------------------------------------------------------
    const outlineToTreeData = (outline: OutlineItem[]): DataNode[] => {
        return outline.map(item => ({
            key: item.id,
            title: (
                <div className="custom-tree-node group">
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', overflow: 'hidden' }}>
                        <span style={{ marginRight: 8, color: item.level === 1 ? '#1890ff' : '#8c8c8c' }}>
                            {item.children && item.children.length > 0 ? <FolderOpenOutlined /> : <FileOutlined />}
                        </span>
                        <Text strong={item.level === 1} style={{ fontSize: item.level === 1 ? 16 : 14, color: '#262626', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginRight: 16 }}>
                            {item.title}
                        </Text>
                        {item.level === 1 && <Tag color="blue">章</Tag>}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div onClick={(e) => e.stopPropagation()}>
                            <InputNumber
                                addonAfter="字"
                                size="small"
                                min={0}
                                step={100}
                                value={item.wordCount}
                                onChange={(value) => handleWordCountChange(item.id, value)} 
                                parser={value => value?.replace('字', '') as unknown as number}
                                style={{ width: 140, opacity: item.wordCount ? 1 : 0.6 }}
                                placeholder="未设定"
                            />
                        </div>

                        <Space className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            <Tooltip title="修改标题"><Button type="text" size="small" icon={<EditOutlined style={{ color: '#1890ff' }} />} onClick={(e) => { e.stopPropagation(); openModal('edit', item); }} /></Tooltip>
                            <Tooltip title="添加子章节"><Button type="text" size="small" icon={<PlusOutlined style={{ color: '#52c41a' }} />} onClick={(e) => { e.stopPropagation(); openModal('add', item); }} /></Tooltip>
                            <Popconfirm title="确定删除？" onConfirm={(e) => { e?.stopPropagation(); handleDeleteNode(item.id); }} onCancel={(e) => e?.stopPropagation()} okText="删除" cancelText="取消">
                                <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                            </Popconfirm>
                        </Space>
                    </div>
                </div>
            ),
            children: item.children ? outlineToTreeData(item.children) : undefined,
        }));
    };

    // -------------------------------------------------------------------------
    // 5. API 调用 (后台并行生成)
    // -------------------------------------------------------------------------
    const handleGenerateOutline = async () => {
        if (!state.documentContent || !state.overview || !state.requirements) {
            message.error('请先完成文档分析步骤！');
            return;
        }
        setLoading(true);
        try {
            const result = await generateOutline(state.overview, state.requirements, state.config);
            setState({ outline: result, currentStep: ProcessStep.OUTLINE_EDIT });
            message.success('AI 目录已刷新');
        } catch (error) {
            message.error('生成失败');
        } finally {
            setLoading(false);
        }
    };

    // 🚀 核心修改：非阻塞式后台生成
    const handleGenerateContent = () => {
        if (state.outline.length === 0) {
             message.warning('目录为空');
             return;
        }

        // 1. 设置全局生成状态
        setState({ isGenerating: true });

        // 2. 启动后台流式任务 (不等待)
        generateContentStream(
            state.documentContent, 
            state.overview, 
            state.requirements, 
            state.outline, 
            state.config,
            (chapterId, content) => {
                // 实时更新全局状态
                setState((prev: AppState) => ({
                    ...prev,
                    generatedContent: {
                        ...prev.generatedContent,
                        [chapterId]: content
                    }
                }));
            }
        ).then(() => {
            setState({ isGenerating: false });
            message.success({ content: '🎉 所有章节内容生成完成！', duration: 5 });
        }).catch((error) => {
            console.error(error);
            setState({ isGenerating: false });
            message.error('生成过程中断，请检查网络或后端服务');
        });

        // 3. 立即引导跳转
        Modal.success({
            title: '🚀 内容生成已启动',
            content: (
                <div>
                    <p>AI 正在后台并行生成所有章节内容。</p>
                    <p>您可以立即前往<b>编辑页面</b>，内容将实时逐章呈现。</p>
                </div>
            ),
            okText: '立即前往编辑',
            onOk: () => {
                onNext(); 
            },
            cancelText: '稍后',
            closable: true,
        });
    };

    return (
        <Card 
            title={<Space><FileTextOutlined /><span>AI 生成目录与字数设定</span></Space>} 
            style={{ minHeight: '80vh', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
            extra={<Button onClick={handleGenerateOutline} loading={loading} icon={<FileTextOutlined />}>重置目录</Button>}
        >
            <style>{treeStyles}</style>
            
            <Spin spinning={loading} tip="AI 正在构建目录结构...">
                {state.outline.length === 0 ? (
                    <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={<Space direction="vertical"><Text type="secondary">暂无目录数据</Text><Button type="primary" onClick={handleGenerateOutline}>立即生成目录</Button></Space>}
                        style={{ padding: '60px 0' }}
                    />
                ) : (
                    <>
                        <div style={{ marginBottom: 20, backgroundColor: '#f0f5ff', padding: '16px 24px', borderRadius: 8, border: '1px solid #d6e4ff' }}>
                            <Row gutter={24} align="middle">
                                <Col flex="auto">
                                    <Space size="large">
                                        <Space>
                                            <AimOutlined style={{ color: '#1890ff', fontSize: 20 }} />
                                            <div>
                                                <Text strong style={{ fontSize: 16 }}>全文总字数目标</Text>
                                                <div style={{ fontSize: 12, color: '#666' }}>系统将自动将总字数分配给各章节</div>
                                            </div>
                                        </Space>
                                        <InputNumber 
                                            size="large"
                                            style={{ width: 200 }} 
                                            value={totalTargetWords}
                                            onChange={(val) => setTotalTargetWords(val || 0)}
                                            step={1000}
                                            addonAfter="字"
                                        />
                                        <Button 
                                            type="primary" 
                                            icon={<CalculatorOutlined />} 
                                            onClick={handleDistributeWords}
                                        >
                                            一键智能分配
                                        </Button>
                                    </Space>
                                </Col>
                                <Col>
                                    <Tag color="orange">支持拖拽调整结构</Tag>
                                </Col>
                            </Row>
                        </div>

                        <div style={{ maxHeight: '60vh', overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 8, backgroundColor: '#fff' }}>
                            <Tree
                                className="draggable-tree"
                                draggable
                                blockNode 
                                onDrop={onDrop}
                                showLine={{ showLeafIcon: false }}
                                defaultExpandAll
                                treeData={outlineToTreeData(state.outline)}
                                selectable={false} 
                                style={{ padding: '8px 0' }}
                            />
                        </div>

                        <div style={{ textAlign: 'right', marginTop: 24, padding: '16px 0', borderTop: '1px solid #f0f0f0' }}>
                            <Button type="primary" size="large" onClick={handleGenerateContent} disabled={state.outline.length === 0} icon={<SaveOutlined />} style={{ paddingLeft: 32, paddingRight: 32 }}>
                                确认目录并生成内容
                            </Button>
                        </div>
                    </>
                )}
            </Spin>

            <Modal title={modalMode === 'add' ? "添加子章节" : "修改章节标题"} open={isModalOpen} onOk={handleModalOk} onCancel={() => setIsModalOpen(false)} destroyOnClose maskClosable={false}>
                <div style={{ paddingTop: 16, paddingBottom: 16 }}>
                    <Text strong style={{ marginBottom: 8, display: 'block' }}>章节标题</Text>
                    <Input placeholder="请输入章节标题" value={modalInputValue} onChange={(e) => setModalInputValue(e.target.value)} onPressEnter={handleModalOk} autoFocus size="large"/>
                </div>
            </Modal>
        </Card>
    );
};

export default OutlineEdit;