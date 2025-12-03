import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message, Popconfirm, Upload, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, SyncOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

interface DatabaseRecord {
    id: string;
    name: string;
    description: string;
    file_path: string;
    chunk_count: number;
    created_at: string;
    updated_at: string;
    status: string;
}

interface FormValues {
    name: string;
    description: string;
    file?: any;
}

const DatabaseManagementTab: React.FC = () => {
    const [databases, setDatabases] = useState<DatabaseRecord[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [modalVisible, setModalVisible] = useState<boolean>(false);
    const [editingRecord, setEditingRecord] = useState<DatabaseRecord | null>(null);
    const [form] = Form.useForm();
    const [uploading, setUploading] = useState<boolean>(false);

    // 加载数据库列表
    const loadDatabases = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_BASE_URL}/api/knowledge/list`);
            setDatabases(response.data.databases || []);
        } catch (error) {
            message.error('加载知识库列表失败');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDatabases();
    }, []);

    // 打开新建/编辑对话框
    const handleAdd = () => {
        setEditingRecord(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (record: DatabaseRecord) => {
        setEditingRecord(record);
        form.setFieldsValue({
            name: record.name,
            description: record.description,
        });
        setModalVisible(true);
    };

    // 删除知识库
    const handleDelete = async (id: string) => {
        try {
            await axios.delete(`${API_BASE_URL}/api/knowledge/delete/${id}`);
            message.success('删除成功');
            loadDatabases();
        } catch (error) {
            message.error('删除失败');
            console.error(error);
        }
    };

    // 提交表单
    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            setUploading(true);

            if (editingRecord) {
                // 编辑模式
                await axios.put(`${API_BASE_URL}/api/knowledge/update/${editingRecord.id}`, {
                    name: values.name,
                    description: values.description,
                });
                message.success('更新成功');
            } else {
                // 新建模式 - 上传文件
                if (!values.file || values.file.fileList.length === 0) {
                    message.error('请选择要上传的文件');
                    return;
                }

                const formData = new FormData();
                formData.append('file', values.file.fileList[0].originFileObj);
                formData.append('name', values.name);
                formData.append('description', values.description);

                await axios.post(`${API_BASE_URL}/api/knowledge/upload`, formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                });
                message.success('上传成功');
            }

            setModalVisible(false);
            form.resetFields();
            loadDatabases();
        } catch (error) {
            message.error('操作失败');
            console.error(error);
        } finally {
            setUploading(false);
        }
    };

    // 重新索引
    const handleReindex = async (id: string) => {
        try {
            setLoading(true);
            await axios.post(`${API_BASE_URL}/api/knowledge/reindex/${id}`);
            message.success('重新索引成功');
            loadDatabases();
        } catch (error) {
            message.error('重新索引失败');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    // 表格列定义
    const columns: ColumnsType<DatabaseRecord> = [
        {
            title: '名称',
            dataIndex: 'name',
            key: 'name',
            width: 200,
        },
        {
            title: '描述',
            dataIndex: 'description',
            key: 'description',
            ellipsis: true,
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            width: 100,
            render: (status: string) => {
                const statusConfig: { [key: string]: { color: string; text: string } } = {
                    ready: { color: 'green', text: '就绪' },
                    processing: { color: 'blue', text: '处理中' },
                    error: { color: 'red', text: '错误' },
                };
                const config = statusConfig[status] || { color: 'default', text: status };
                return <Tag color={config.color}>{config.text}</Tag>;
            },
        },
        {
            title: '文档数量',
            dataIndex: 'chunk_count',
            key: 'chunk_count',
            width: 120,
            render: (count: number) => count || 0,
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 180,
            render: (text: string) => new Date(text).toLocaleString('zh-CN'),
        },
        {
            title: '操作',
            key: 'action',
            width: 250,
            fixed: 'right',
            render: (_, record) => (
                <Space size="small">
                    <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        编辑
                    </Button>
                    <Button
                        type="link"
                        size="small"
                        icon={<SyncOutlined />}
                        onClick={() => handleReindex(record.id)}
                        disabled={record.status === 'processing'}
                    >
                        重建索引
                    </Button>
                    <Popconfirm
                        title="确定要删除这个知识库吗?"
                        onConfirm={() => handleDelete(record.id)}
                        okText="确定"
                        cancelText="取消"
                    >
                        <Button
                            type="link"
                            danger
                            size="small"
                            icon={<DeleteOutlined />}
                        >
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div style={{ padding: '24px' }}>
            <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between' }}>
                <h2>知识库管理</h2>
                <Space>
                    <Button icon={<SyncOutlined />} onClick={loadDatabases}>
                        刷新
                    </Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                        新建知识库
                    </Button>
                </Space>
            </div>

            <Table
                columns={columns}
                dataSource={databases}
                rowKey="id"
                loading={loading}
                pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条记录`,
                }}
                scroll={{ x: 1200 }}
            />

            <Modal
                title={editingRecord ? '编辑知识库' : '新建知识库'}
                open={modalVisible}
                onOk={handleSubmit}
                onCancel={() => {
                    setModalVisible(false);
                    form.resetFields();
                }}
                confirmLoading={uploading}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    initialValues={{
                        name: '',
                        description: '',
                    }}
                >
                    <Form.Item
                        label="知识库名称"
                        name="name"
                        rules={[{ required: true, message: '请输入知识库名称' }]}
                    >
                        <Input placeholder="请输入知识库名称" />
                    </Form.Item>

                    <Form.Item
                        label="描述"
                        name="description"
                        rules={[{ required: true, message: '请输入描述' }]}
                    >
                        <Input.TextArea rows={4} placeholder="请输入知识库描述" />
                    </Form.Item>

                    {!editingRecord && (
                        <Form.Item
                            label="上传文件"
                            name="file"
                            rules={[{ required: true, message: '请上传文件' }]}
                        >
                            <Upload
                                accept=".pdf,.doc,.docx,.txt"
                                maxCount={1}
                                beforeUpload={() => false}
                            >
                                <Button icon={<UploadOutlined />}>选择文件</Button>
                            </Upload>
                        </Form.Item>
                    )}

                    {editingRecord && (
                        <Form.Item label="文件路径">
                            <Input value={editingRecord.file_path} disabled />
                        </Form.Item>
                    )}
                </Form>
            </Modal>
        </div>
    );
};

export default DatabaseManagementTab;