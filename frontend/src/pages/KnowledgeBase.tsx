import React, { useState, useEffect } from 'react';
import { Card, Upload, Button, Select, message, Typography, Space, Input, List, Tag, Alert, Modal, Table, Tabs, notification, Progress, Tooltip } from 'antd';
// ✅ 引入 EyeOutlined 图标
import { DeleteOutlined, SearchOutlined, CloudUploadOutlined, ReadOutlined, ReloadOutlined, FileTextOutlined, EyeOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { RcFile } from 'antd/es/upload';
import { uploadKnowledge, resetKnowledge, searchKnowledge, getKnowledgeList, deleteKnowledgeFile } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;
const { Option } = Select;

const KnowledgeBase: React.FC = () => {
    const [uploading, setUploading] = useState(false);
    const [docType, setDocType] = useState('general');
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<string[]>([]);
    const [searching, setSearching] = useState(false);

    // 列表状态
    const [listData, setListData] = useState<any[]>([]);
    const [listLoading, setListLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });

    // ✅ 新增：查看详情弹窗状态
    const [viewModalOpen, setViewModalOpen] = useState(false);
    const [viewContent, setViewContent] = useState('');
    const [viewSource, setViewSource] = useState('');

    const [api, contextHolder] = notification.useNotification();

    useEffect(() => {
        fetchList(1, 10);
    }, []);

    const fetchList = async (page: number, pageSize: number) => {
        setListLoading(true);
        try {
            const offset = (page - 1) * pageSize;
            const res = await getKnowledgeList(pageSize, offset);
            setListData(res.items);
            setTotal(res.total);
            setPagination({ current: page, pageSize });
        } catch (e) {
            message.error("获取知识库列表失败");
        } finally {
            setListLoading(false);
        }
    };

    const handleDeleteFile = (source: string) => {
        Modal.confirm({
            title: `确认删除文件 "${source}"？`,
            content: '该文件及其所有关联的知识片段将被永久删除。',
            okText: '删除',
            okType: 'danger',
            cancelText: '取消',
            onOk: async () => {
                try {
                    await deleteKnowledgeFile(source);
                    message.success("删除成功");
                    fetchList(pagination.current, pagination.pageSize); 
                } catch (e) {
                    message.error("删除失败");
                }
            }
        });
    };

    // ✅ 新增：处理查看点击
    const handleViewContent = (record: any) => {
        setViewContent(record.content);
        setViewSource(record.source);
        setViewModalOpen(true);
    };

    const columns = [
        {
            title: '来源文件',
            dataIndex: 'source',
            key: 'source',
            width: 220,
            render: (text: string) => <Tag icon={<FileTextOutlined />} color="blue" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{text}</Tag>
        },
        {
            title: '类型',
            dataIndex: 'type',
            key: 'type',
            width: 100,
            render: (text: string) => {
                const colors: any = { general: 'default', product: 'cyan', history: 'purple', qualification: 'gold' };
                const labels: any = { general: '通用', product: '产品', history: '历史标书', qualification: '资质' };
                return <Tag color={colors[text] || 'default'}>{labels[text] || text}</Tag>;
            }
        },
        {
            title: '内容预览',
            dataIndex: 'content',
            key: 'content',
            render: (text: string) => (
                <div style={{ maxHeight: 50, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', color: '#666', fontSize: 13 }}>
                    {text}
                </div>
            )
        },
        {
            title: '操作',
            key: 'action',
            width: 160,
            render: (_: any, record: any) => (
                <Space>
                    {/* ✅ 新增查看按钮 */}
                    <Button 
                        type="link" 
                        size="small" 
                        icon={<EyeOutlined />} 
                        onClick={() => handleViewContent(record)}
                    >
                        查看
                    </Button>
                    <Tooltip title="将删除该文件来源的所有切片">
                        <Button type="link" danger size="small" icon={<DeleteOutlined />} onClick={() => handleDeleteFile(record.source)}>
                            删除文件
                        </Button>
                    </Tooltip>
                </Space>
            ),
        },
    ];

    const customRequest = async (options: any) => {
        const { file, onSuccess, onError } = options;
        const rcFile = file as RcFile;
        const key = `upload-${rcFile.uid}`;

        setUploading(true);

        api.open({
            key,
            message: '正在上传文档...',
            description: (
                <div style={{ width: 280 }}>
                    <Progress percent={0} size="small" status="active" />
                    <div style={{ marginTop: 4, fontSize: 12, color: '#888' }}>
                        准备上传: {rcFile.name}
                    </div>
                </div>
            ),
            placement: 'bottomRight',
            duration: 0, 
            icon: <CloudUploadOutlined style={{ color: '#1890ff' }} />,
        });

        try {
            const res = await uploadKnowledge(rcFile, docType, (percent) => {
                api.open({
                    key,
                    message: percent < 100 ? '正在上传文档...' : '正在解析入库...',
                    description: (
                        <div style={{ width: 280 }}>
                            <Progress 
                                percent={percent} 
                                size="small" 
                                status={percent === 100 ? 'active' : 'active'} 
                                showInfo={true}
                            />
                            <div style={{ marginTop: 4, fontSize: 12, color: '#888' }}>
                                {percent < 100 ? '数据传输中...' : '服务端正在解析切片，请稍候...'}
                            </div>
                        </div>
                    ),
                    placement: 'bottomRight',
                    duration: 0,
                });
            });

            api.success({
                key,
                message: '处理完成',
                description: `文件 ${rcFile.name} 已成功入库，新增 ${res.chunks_added} 个知识片段。`,
                placement: 'bottomRight',
                duration: 4.5,
            });
            
            onSuccess?.(res);
            fetchList(1, 10); 
        } catch (err: any) {
            api.error({
                key,
                message: '入库失败',
                description: `文件 ${rcFile.name} 处理出错: ${err.message}`,
                placement: 'bottomRight',
                duration: 4.5,
            });
            onError?.(err);
        } finally {
            setUploading(false);
        }
    };

    const uploadProps: UploadProps = {
        name: 'file',
        multiple: true,
        showUploadList: false,
        customRequest: customRequest,
    };

    const handleReset = async () => {
        Modal.confirm({
            title: '确认清空知识库？',
            content: '此操作不可恢复，所有已上传的企业文档将被删除。',
            okText: '确认清空',
            okType: 'danger',
            cancelText: '取消',
            onOk: async () => {
                try {
                    await resetKnowledge();
                    message.success('知识库已清空');
                    setSearchResults([]);
                    fetchList(1, 10);
                } catch (e) {
                    message.error('清空失败');
                }
            }
        });
    };

    const handleSearch = async () => {
        if (!searchQuery.trim()) return;
        setSearching(true);
        try {
            const res = await searchKnowledge(searchQuery);
            const results = Array.isArray(res.results) ? res.results : [res.results];
            setSearchResults(results);
            if (results.length === 0 || !results[0]) message.info('未检索到相关内容');
        } catch (e) {
            message.error('检索失败');
        } finally {
            setSearching(false);
        }
    };

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
            {contextHolder}

            <Space direction="vertical" size="large" style={{ width: '100%' }}>
                
                <div style={{ textAlign: 'center', marginBottom: 10 }}>
                    <Title level={2}><ReadOutlined /> 企业知识库管理</Title>
                    <Paragraph type="secondary">
                        管理企业私有知识库，支持 PDF/Word 上传、自动切片、向量检索与内容预览。
                    </Paragraph>
                </div>

                <Tabs defaultActiveKey="list" items={[
                    {
                        key: 'list',
                        label: '📚 知识库概览',
                        children: (
                            <Card title={
                                <div style={{display:'flex', justifyContent:'space-between'}}>
                                    <span>已存入的知识片段 (共 {total} 条)</span>
                                    <Button icon={<ReloadOutlined />} size="small" onClick={() => fetchList(pagination.current, pagination.pageSize)}>刷新</Button>
                                </div>
                            } bordered={false}>
                                <Table 
                                    columns={columns} 
                                    dataSource={listData} 
                                    rowKey="id"
                                    loading={listLoading}
                                    pagination={{
                                        current: pagination.current,
                                        pageSize: pagination.pageSize,
                                        total: total,
                                        onChange: (page, pageSize) => fetchList(page, pageSize),
                                        showTotal: (total) => `共 ${total} 条`
                                    }}
                                />
                            </Card>
                        )
                    },
                    {
                        key: 'upload',
                        label: '☁️ 文档入库',
                        children: (
                            <Card title="上传新文档" bordered={false}>
                                <Space style={{ marginBottom: 16 }}>
                                    <Text strong>文档类型：</Text>
                                    <Select value={docType} onChange={setDocType} style={{ width: 200 }}>
                                        <Option value="general">通用资料</Option>
                                        <Option value="product">产品/技术参数表</Option>
                                        <Option value="history">历史成功案例/标书</Option>
                                        <Option value="qualification">企业资质/证书</Option>
                                    </Select>
                                    <Tag color="blue">支持 PDF, Word (.docx)</Tag>
                                </Space>
                                <Dragger {...uploadProps} style={{ padding: 40, background: '#fafafa', border: '2px dashed #d9d9d9' }}>
                                    <p className="ant-upload-drag-icon"><CloudUploadOutlined style={{ color: '#1890ff' }} /></p>
                                    <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
                                    <p className="ant-upload-hint">支持批量上传，右下角将显示处理进度</p>
                                </Dragger>
                            </Card>
                        )
                    },
                    {
                        key: 'search',
                        label: '🔍 检索测试',
                        children: (
                            <Card title="效果验证" bordered={false}>
                                <Space.Compact style={{ width: '100%', marginBottom: 20 }}>
                                    <Input 
                                        placeholder="输入问题测试检索效果..." 
                                        value={searchQuery}
                                        onChange={e => setSearchQuery(e.target.value)}
                                        onPressEnter={handleSearch}
                                        size="large"
                                    />
                                    <Button type="primary" size="large" icon={<SearchOutlined />} loading={searching} onClick={handleSearch}>检索</Button>
                                </Space.Compact>
                                {searchResults.length > 0 && (
                                    <List
                                        dataSource={searchResults}
                                        renderItem={(item, index) => (
                                            <List.Item>
                                                <Card size="small" style={{ width: '100%', background: '#f6ffed' }}>
                                                    <Tag color="green">Result {index + 1}</Tag>
                                                    <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{item}</div>
                                                </Card>
                                            </List.Item>
                                        )}
                                    />
                                )}
                            </Card>
                        )
                    },
                    {
                        key: 'danger',
                        label: '⚠️ 危险区',
                        children: (
                            <Card bordered={false} style={{ borderColor: '#ffccc7', background: '#fff1f0' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Text type="danger">清空整个知识库（此操作不可恢复）</Text>
                                    <Button danger icon={<DeleteOutlined />} onClick={handleReset}>立即清空</Button>
                                </div>
                            </Card>
                        )
                    }
                ]} />

            </Space>

            {/* ✅ 新增：查看完整内容的模态框 */}
            <Modal
                title={
                    <Space>
                        <FileTextOutlined />
                        <span>知识片段详情</span>
                        <Tag color="blue">{viewSource}</Tag>
                    </Space>
                }
                open={viewModalOpen}
                onCancel={() => setViewModalOpen(false)}
                footer={[
                    <Button key="close" onClick={() => setViewModalOpen(false)}>
                        关闭
                    </Button>
                ]}
                width={800}
                centered
            >
                <div style={{ 
                    maxHeight: '60vh', 
                    overflowY: 'auto', 
                    whiteSpace: 'pre-wrap', 
                    padding: '16px', 
                    background: '#f5f5f5', 
                    borderRadius: '4px',
                    border: '1px solid #e8e8e8',
                    fontFamily: 'Consolas, "Courier New", monospace',
                    fontSize: '14px',
                    lineHeight: '1.6'
                }}>
                    {viewContent}
                </div>
            </Modal>
        </div>
    );
};

export default KnowledgeBase;