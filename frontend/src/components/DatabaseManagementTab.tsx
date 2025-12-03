import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Button, Space, Select, message, Modal, Form, Input, Typography, Tag, Tooltip, Alert } from 'antd';
import { DatabaseOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, PlusOutlined, EyeOutlined } from '@ant-design/icons';
import { getAvailableTables, listCompanyRecords, deleteRecord, createCompanyRecord, updateCompanyRecord } from '../services/api';

const { Option } = Select;
const { Text } = Typography;

// 示例表结构，用于动态渲染表单和表格
const TABLE_METADATA: Record<string, { label: string, fields: Array<{key: string, label: string, type: string, required: boolean}> }> = {
    't_company': {
        label: '公司基本信息表',
        fields: [
            { key: 'id', label: 'ID (主键)', type: 'string', required: false },
            { key: 'company_name', label: '公司名称', type: 'string', required: true },
            { key: 'parent_id', label: '父节点ID', type: 'string', required: false },
            { key: 'address', label: '公司地址', type: 'string', required: false },
            { key: 'created_time', label: '创建时间', type: 'datetime', required: false },
            { key: 'updated_time', label: '修改时间', type: 'datetime', required: false },
        ]
    },
    't_person': { // 占位示例
        label: '企业人员信息表',
        fields: [
            { key: 'id', label: 'ID (主键)', type: 'string', required: false },
            { key: 'person_name', label: '人员姓名', type: 'string', required: true },
            { key: 'position', label: '岗位', type: 'string', required: false },
        ]
    }
    // ... 更多表
};


const DatabaseManagementTab: React.FC = () => {
    const [availableTables, setAvailableTables] = useState<Array<{ name: string, description: string }>>([]);
    const [selectedTable, setSelectedTable] = useState<string>('t_company');
    const [tableData, setTableData] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
    
    // Modal 状态
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
    const [editingRecord, setEditingRecord] = useState<any | null>(null);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchAvailableTables();
    }, []);

    useEffect(() => {
        if (selectedTable) {
            fetchData(1, pagination.pageSize, selectedTable);
        }
    }, [selectedTable]);

    const fetchAvailableTables = async () => {
        try {
            const res = await getAvailableTables();
            setAvailableTables(res.tables);
            // 默认选中第一个可管理的表
            if (res.tables.length > 0 && res.tables.find((t: any) => t.name === 't_company')) {
                 setSelectedTable('t_company');
            } else if (res.tables.length > 0) {
                 setSelectedTable(res.tables[0].name);
            }
        } catch (e) {
            message.error("获取可用表列表失败");
        }
    };

    const fetchData = async (page: number, pageSize: number, tableName: string) => {
        setLoading(true);
        try {
            const offset = (page - 1) * pageSize;
            // ⚠️ 注意：这里需要根据表名调用不同的 API 函数，目前仅实现 t_company 的列表
            // 未来应扩展 listData 通用函数或使用 switch case
            const res = await listCompanyRecords(pageSize, offset); 
            setTableData(res.items);
            setTotal(res.total);
            setPagination({ current: page, pageSize });
        } catch (e) {
            message.error(`获取表 ${tableName} 数据失败`);
        } finally {
            setLoading(false);
        }
    };
    
    // --- 增删改查事件 ---
    
    const handleCreate = () => {
        setModalMode('create');
        setEditingRecord(null);
        form.resetFields();
        setIsModalVisible(true);
    };

    const handleEdit = (record: any) => {
        setModalMode('edit');
        setEditingRecord(record);
        // 自动设置表单值
        form.setFieldsValue(record);
        setIsModalVisible(true);
    };

    const handleDelete = (recordId: string) => {
        Modal.confirm({
            title: `确认删除 ${selectedTable} 中 ID 为 "${recordId}" 的记录?`,
            content: '此操作不可恢复。',
            okText: '删除',
            okType: 'danger',
            cancelText: '取消',
            onOk: async () => {
                try {
                    await deleteRecord(selectedTable, recordId);
                    message.success('删除成功');
                    fetchData(pagination.current, pagination.pageSize, selectedTable);
                } catch (e: any) {
                    message.error(`删除失败: ${e.message || '未知错误'}`);
                }
            }
        });
    };
    
    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            setLoading(true);
            
            if (modalMode === 'create') {
                await createCompanyRecord(values);
                message.success('新增记录成功');
            } else if (modalMode === 'edit' && editingRecord) {
                await updateCompanyRecord(editingRecord.id, values);
                message.success('更新记录成功');
            }

            setIsModalVisible(false);
            form.resetFields();
            // 刷新当前页数据
            fetchData(pagination.current, pagination.pageSize, selectedTable);
            
        } catch (e) {
            message.error('操作失败，请检查输入或联系管理员');
        } finally {
            setLoading(false);
        }
    };

    // --- 表格列渲染 ---
    
    const columns = useMemo(() => {
        if (!TABLE_METADATA[selectedTable]) {
            // 如果表元数据不存在，则尝试从第一条数据中动态生成列
            if (tableData.length === 0) return [];
            return Object.keys(tableData[0]).map(key => ({
                title: key,
                dataIndex: key,
                key: key,
                render: (text: any) => <Tooltip title={String(text)}>{String(text).length > 20 ? `${String(text).substring(0, 20)}...` : String(text)}</Tooltip>
            }));
        }

        const baseColumns = TABLE_METADATA[selectedTable].fields
            .filter(field => field.key !== 'id') // 隐藏 ID 字段，但在操作中显示
            .map(field => ({
                title: field.label,
                dataIndex: field.key,
                key: field.key,
                render: (text: any) => {
                    const content = String(text);
                    if (field.type === 'datetime') return <Tag color="blue">{content}</Tag>;
                    return <Tooltip title={content}>{content.length > 20 ? `${content.substring(0, 20)}...` : content}</Tooltip>;
                }
            }));
            
        // 添加操作列
        baseColumns.push({
            title: '操作',
            key: 'action',
            width: 150,
            render: (_: any, record: any, _index: number) => ( 
                <Space size="small">
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
                    <Button type="link" danger size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>删除</Button>
                </Space>
            )
        });
        
        // 增加 ID 预览列
        baseColumns.unshift({
             title: 'ID',
             dataIndex: 'id',
             key: 'id',
             width: 100,
             render: (text: string) => <Tag color="default"><Tooltip title={text}>{text.substring(0, 4)}...</Tooltip></Tag>
        })

        return baseColumns;
    }, [selectedTable, tableData]);

    const handleTableChange = (table: string) => {
        setSelectedTable(table);
        setTableData([]);
    };
    
    // --- Modal 表单渲染 ---

    const renderFormItems = () => {
        const metadata = TABLE_METADATA[selectedTable];
        if (!metadata) return <Alert message="请选择一个可管理的表" type="warning" />;
        
        return metadata.fields
            .filter(f => f.key !== 'id' && !f.key.startsWith('created_') && !f.key.startsWith('updated_')) // 隐藏ID和审计字段
            .map(field => (
                <Form.Item
                    key={field.key}
                    label={field.label}
                    name={field.key}
                    rules={[{ required: field.required, message: `请输入 ${field.label}` }]}
                >
                    <Input placeholder={`请输入 ${field.label}`} disabled={field.type === 'datetime'} />
                </Form.Item>
            ));
    };

    return (
        <Card 
            title={<Space><DatabaseOutlined /><span>结构化数据管理</span></Space>} 
            style={{ minHeight: '80vh' }}
            extra={
                <Space>
                    <Select value={selectedTable} onChange={handleTableChange} style={{ width: 200 }}>
                        {availableTables.map(table => (
                            <Option key={table.name} value={table.name}>
                                {table.description} ({table.name})
                            </Option>
                        ))}
                    </Select>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增记录</Button>
                    <Button icon={<ReloadOutlined />} onClick={() => fetchData(pagination.current, pagination.pageSize, selectedTable)}>刷新</Button>
                </Space>
            }
        >
            {/* 修正：这里使用了 Alert 组件 */}
            <Alert 
                message={<Text strong>当前表: {TABLE_METADATA[selectedTable]?.label || selectedTable}</Text>} 
                description={<Text type="secondary">本界面仅演示 `t_company` 表的增删改查功能。如需管理其他表，请在后端 `table_service.py` 和前端 `DatabaseManagementTab.tsx` 中扩展相应的 ORM 模型和 API 调用。</Text>}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
            />
            
            <Table
                columns={columns}
                dataSource={tableData}
                rowKey="id"
                loading={loading}
                pagination={{
                    current: pagination.current,
                    pageSize: pagination.pageSize,
                    total: total,
                    onChange: (page, pageSize) => fetchData(page, pageSize, selectedTable),
                    showTotal: (total) => `共 ${total} 条`
                }}
            />

            <Modal 
                title={modalMode === 'create' ? `新增 ${TABLE_METADATA[selectedTable]?.label || selectedTable} 记录` : `编辑 ${editingRecord?.id.substring(0, 8)}... 记录`} 
                open={isModalVisible} 
                onOk={handleModalOk} 
                onCancel={() => setIsModalVisible(false)} 
                confirmLoading={loading}
                destroyOnClose
            >
                <Form form={form} layout="vertical" initialValues={editingRecord}>
                    {renderFormItems()}
                </Form>
            </Modal>
        </Card>
    );
};

export default DatabaseManagementTab;