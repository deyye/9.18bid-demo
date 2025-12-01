import React, { useState } from 'react';
import { Card, Upload, Button, Select, message, Typography, Space, Divider, Input, List, Tag, Alert, Modal } from 'antd';
import { InboxOutlined, DeleteOutlined, SearchOutlined, CloudUploadOutlined, ReadOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { uploadKnowledge, resetKnowledge, searchKnowledge } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;
const { Option } = Select;
const { TextArea } = Input;

const KnowledgeBase: React.FC = () => {
    const [uploading, setUploading] = useState(false);
    const [docType, setDocType] = useState('general');
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<string[]>([]);
    const [searching, setSearching] = useState(false);

    // 上传配置
    const uploadProps: UploadProps = {
        name: 'file',
        multiple: true,
        showUploadList: false, // 我们手动处理反馈，不显示默认列表
        customRequest: async (options) => {
            const { file, onSuccess, onError } = options;
            setUploading(true);
            try {
                const res = await uploadKnowledge(file as File, docType);
                message.success(`${(file as File).name} 上传成功，新增 ${res.chunks_added} 个知识片段`);
                onSuccess?.(res);
            } catch (err: any) {
                message.error(`${(file as File).name} 上传失败: ${err.message}`);
                onError?.(err);
            } finally {
                setUploading(false);
            }
        },
    };

    // 重置知识库
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
                } catch (e) {
                    message.error('清空失败');
                }
            }
        });
    };

    // 测试检索
    const handleSearch = async () => {
        if (!searchQuery.trim()) return;
        setSearching(true);
        try {
            const res = await searchKnowledge(searchQuery);
            // 假设后端返回的是 { results: "string..." } 或 { results: ["..."] }
            // 这里根据你的 rag_service.search 实现，它返回的是 List[str]
            const results = Array.isArray(res.results) ? res.results : [res.results];
            setSearchResults(results);
            if (results.length === 0 || !results[0]) {
                message.info('未检索到相关内容');
            }
        } catch (e) {
            message.error('检索失败');
        } finally {
            setSearching(false);
        }
    };

    return (
        <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
                
                {/* 顶部介绍 */}
                <div style={{ textAlign: 'center', marginBottom: 20 }}>
                    <Title level={2}><ReadOutlined /> 企业知识库管理</Title>
                    <Paragraph type="secondary">
                        在此上传企业产品手册、历史标书、资质证明等文档。AI 在生成标书时，会自动检索并引用这些内容，确保生成的标书符合企业实际情况。
                    </Paragraph>
                </div>

                {/* 1. 上传区域 */}
                <Card title="📄 文档入库" bordered={false} style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
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
                        <p className="ant-upload-drag-icon">
                            <CloudUploadOutlined style={{ color: '#1890ff' }} />
                        </p>
                        <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
                        <p className="ant-upload-hint">
                            系统会自动解析文档内容并存入向量数据库 (ChromaDB)
                        </p>
                    </Dragger>
                </Card>

                {/* 2. 检索测试区域 */}
                <Card title="🔍 效果验证 (RAG 检索测试)" bordered={false} style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
                    <Alert message="在此输入问题，测试 AI 能否从知识库中找到对应的答案。" type="info" showIcon style={{ marginBottom: 16 }} />
                    <Space.Compact style={{ width: '100%' }}>
                        <Input 
                            placeholder="例如：我们公司的核心技术优势是什么？某某产品的参数是多少？" 
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            onPressEnter={handleSearch}
                            size="large"
                        />
                        <Button type="primary" size="large" icon={<SearchOutlined />} loading={searching} onClick={handleSearch}>
                            检索
                        </Button>
                    </Space.Compact>

                    {searchResults.length > 0 && (
                        <div style={{ marginTop: 24 }}>
                            <Title level={5}>检索结果片段：</Title>
                            <List
                                dataSource={searchResults}
                                renderItem={(item, index) => (
                                    <List.Item>
                                        <Card size="small" style={{ width: '100%', background: '#f6ffed', borderColor: '#b7eb8f' }}>
                                            <Tag color="green">片段 {index + 1}</Tag>
                                            <div style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{item}</div>
                                        </Card>
                                    </List.Item>
                                )}
                            />
                        </div>
                    )}
                </Card>

                {/* 3. 危险操作区 */}
                <Card title="⚠️ 危险操作" bordered={false} style={{ borderColor: '#ffccc7' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Text>清空当前所有知识库数据，操作无法撤销。</Text>
                        <Button danger icon={<DeleteOutlined />} onClick={handleReset}>清空知识库</Button>
                    </div>
                </Card>

            </Space>
        </div>
    );
};

export default KnowledgeBase;