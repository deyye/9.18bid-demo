import React, { useState, useEffect } from 'react';
// ✅ 引入 Modal, Table 等组件
import { Card, Upload, Button, Select, message, Typography, Space, Input, List, Tag, Alert, Modal, Table, Tabs } from 'antd';
import { InboxOutlined, DeleteOutlined, SearchOutlined, CloudUploadOutlined, ReadOutlined, ReloadOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
// ✅ 引入新 API
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

    // 初始加载列表
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

    // 删除文件逻辑
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
                    fetchList(pagination.current, pagination.pageSize); // 刷新列表
                } catch (e) {
                    message.error("删除失败");
                }
            }
        });
    };

    // 表格列定义
    const columns = [
        {
            title: '来源文件',
            dataIndex: 'source',
            key: 'source',
            width: 200,
            render: (text: string) => <Tag color="blue">{text}</Tag>
        },
        {
            title: '类型',
            dataIndex: 'type',
            key: 'type',
            width: 120,
            render: (text: string) => {
                const colors: any = { general: 'default', product: 'cyan', history: 'purple', qualification: 'gold' };
                return <Tag color={colors[text] || 'default'}>{text}</Tag>;
            }
        },
        {
            title: '内容预览',
            dataIndex: 'content',
            key: 'content',
            render: (text: string) => (
                <div style={{ maxHeight: 60, overflow: 'hidden', textOverflow: 'ellipsis', color: '#666', fontSize: 13 }}>
                    {text}
                </div>
            )
        },
        {
            title: '操作',
            key: 'action',
            width: 100,
            render: (_: any, record: any) => (
                <Button type="link" danger size="small" onClick={() => handleDeleteFile(record.source)}>
                    删除文件
                </Button>
            ),
        },
    ];

    // 上传配置
    const uploadProps: UploadProps = {
        name: 'file',
        multiple: true,
        showUploadList: false,
        customRequest: async (options) => {
            const { file, onSuccess, onError } = options;
            setUploading(true);
            try {
                const res = await uploadKnowledge(file as File, docType);
                message.success(`${(file as File).name} 上传成功，新增 ${res.chunks_added} 个片段`);
                onSuccess?.(res);
                fetchList(1, 10); // 上传成功后刷新第一页
            } catch (err: any) {
                message.error(`${(file as File).name} 上传失败: ${err.message}`);
                onError?.(err);
            } finally {
                setUploading(false);
            }
        },
    };

    // 重置
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

    // 搜索
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
                                    <p className="ant-upload-hint">系统会自动解析并切片存入 RAG 数据库</p>
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
        </div>
    );
};

export default KnowledgeBase;