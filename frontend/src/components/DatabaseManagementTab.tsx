import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Button, Space, Select, message, Modal, Form, Input, Typography, Tag, Tooltip, Alert } from 'antd';
import { DatabaseOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { 
    getAvailableTables, 
    listTableRecords, 
    deleteRecord, 
    createCompanyRecord, 
    updateCompanyRecord 
} from '../services/api';

const { Option } = Select;
const { Text } = Typography;

// 表结构定义（用于前端渲染表格和表单）
const TABLE_METADATA: Record<string, { label: string, fields: Array<{key: string, label: string, type: 'string' | 'datetime' | 'number' | 'date', required: boolean}> }> = {
    // 1. 公司信息
    't_company': {
        label: '公司信息表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'company_name', label: '公司名称', type: 'string', required: true },
            { key: 'parent_id', label: '父节点ID', type: 'string', required: false },
            { key: 'address', label: '地址', type: 'string', required: false },
            { key: 'created_time', label: '创建时间', type: 'datetime', required: false },
        ]
    },
    't_attachment': {
        label: '系统附件表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'external_id', label: '关联ID', type: 'string', required: true },
            { key: 'external_type', label: '关联类型', type: 'string', required: true },
            { key: 'file_url', label: '文件地址', type: 'string', required: true },
            { key: 'file_type', label: '文件类型', type: 'string', required: false },
        ]
    },
    // 2. 资质认证
    't_business_certification': {
        label: '资质认证表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'company_id', label: '关联公司ID', type: 'string', required: true },
            { key: 'certificate_number', label: '证书编号', type: 'string', required: false },
            { key: 'certification_type', label: '资质类型', type: 'string', required: false },
            { key: 'validity_period', label: '有效期', type: 'date', required: false },
            { key: 'issuing_authority', label: '发证机构', type: 'string', required: false },
        ]
    },
    // 3. 知识产权
    't_patent': {
        label: '专利信息表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'company_id', label: '关联公司ID', type: 'string', required: true },
            { key: 'patent_name', label: '专利名称', type: 'string', required: true },
            { key: 'patent_number', label: '专利号', type: 'string', required: false },
            { key: 'patent_type', label: '专利类型', type: 'string', required: false },
            { key: 'issue_date', label: '发证日期', type: 'date', required: false },
        ]
    },
    't_software_copyright': {
        label: '软件著作权表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'company_id', label: '关联公司ID', type: 'string', required: true },
            { key: 'software_name', label: '软件名称', type: 'string', required: true },
            { key: 'registration_number', label: '登记号', type: 'string', required: false },
            { key: 'issue_date', label: '发证日期', type: 'date', required: false },
        ]
    },
    // 4. 产品管理
    't_product': {
        label: '产品信息表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'company_id', label: '关联公司ID', type: 'string', required: true },
            { key: 'product_name', label: '产品名称', type: 'string', required: true },
            { key: 'product_model', label: '产品型号', type: 'string', required: false },
            { key: 'product_type', label: '产品类型', type: 'string', required: false },
            { key: 'selling_price', label: '售价', type: 'number', required: false },
        ]
    },
    // 5. 人员管理
    't_person': {
        label: '人员信息表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'person_name', label: '姓名', type: 'string', required: true },
            { key: 'id_card', label: '身份证号', type: 'string', required: false },
            { key: 'position', label: '岗位', type: 'string', required: false },
            { key: 'professional_title', label: '职称', type: 'string', required: false },
            { key: 'education', label: '学历', type: 'string', required: false },
        ]
    },
    't_education_background': {
        label: '人员学历表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'person_id', label: '关联人员ID', type: 'string', required: true },
            { key: 'education_name', label: '学历名称', type: 'string', required: true },
        ]
    },
    't_qualification_certificate': {
        label: '人员证书表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'person_id', label: '关联人员ID', type: 'string', required: true },
            { key: 'certificate_name', label: '证书名称', type: 'string', required: true },
            { key: 'certificate_level', label: '等级', type: 'string', required: false },
            { key: 'issue_date', label: '发证日期', type: 'date', required: false },
        ]
    },
    // 6. 项目管理
    't_project': {
        label: '项目投标表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'project_name', label: '项目名称', type: 'string', required: true },
            { key: 'project_number', label: '项目编号', type: 'string', required: false },
            { key: 'bid_time', label: '投标时间', type: 'date', required: false },
            { key: 'bid_quote', label: '投标报价', type: 'number', required: false },
            { key: 'is_win', label: '是否中标', type: 'string', required: false },
        ]
    },
    't_contract': {
        label: '合同信息表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'contract_name', label: '合同名称', type: 'string', required: true },
            { key: 'project_id', label: '关联项目ID', type: 'string', required: true },
            { key: 'contract_amount', label: '合同金额', type: 'number', required: false },
            { key: 'contract_sign_date', label: '签订日期', type: 'date', required: false },
        ]
    },
    't_project_person': {
        label: '项目人员表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'contract_id', label: '关联合同ID', type: 'string', required: true },
            { key: 'person_id', label: '关联人员ID', type: 'string', required: true },
            { key: 'position', label: '项目中职务', type: 'string', required: false },
        ]
    },
    // 7. 招投标管理
    't_bid': {
        label: '投标文件表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'bid_file_name', label: '投标文件名称', type: 'string', required: true },
            { key: 'tender_file_name', label: '招标文件名称', type: 'string', required: false },
        ]
    },
    't_bid_catalogue': {
        label: '投标目录表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'bid_id', label: '关联投标文件ID', type: 'string', required: true },
            { key: 'catalogue_name', label: '目录名称', type: 'string', required: true },
            { key: 'parent_id', label: '父节点ID', type: 'string', required: false },
        ]
    },
    't_bid_file_subentry': {
        label: '投标分项表',
        fields: [
            { key: 'id', label: 'ID', type: 'string', required: false },
            { key: 'bid_id', label: '关联投标文件ID', type: 'string', required: true },
            { key: 'subentry_name', label: '分项名称', type: 'string', required: true },
        ]
    }
};

const DatabaseManagementTab: React.FC = () => {
    // 状态管理
    const [availableTables, setAvailableTables] = useState<Array<{ name: string, description: string }>>([]);
    const [selectedTable, setSelectedTable] = useState<string>('t_company');
    const [tableData, setTableData] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
    
    // 弹窗状态
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
    const [editingRecord, setEditingRecord] = useState<any | null>(null);
    const [form] = Form.useForm();

    // 初始化：获取可用表
    useEffect(() => {
        fetchAvailableTables();
    }, []);

    // 监听表切换：刷新数据
    useEffect(() => {
        if (selectedTable) {
            fetchData(1, pagination.pageSize, selectedTable);
        }
    }, [selectedTable]);

    // 1. 获取可用表列表
    const fetchAvailableTables = async () => {
        try {
            const res = await getAvailableTables();
            setAvailableTables(res.tables);
            // 默认选中 t_company
            if (!selectedTable && res.tables.length > 0) {
                 setSelectedTable('t_company');
            }
        } catch (e) {
            message.error("获取可用表列表失败");
        }
    };

    // 2. 获取表数据 (核心逻辑修正)
    const fetchData = async (page: number, pageSize: number, tableName: string) => {
        setLoading(true);
        try {
            const offset = (page - 1) * pageSize;
            
            // 🟢 修改点：直接调用通用的 listTableRecords
            // 后端 /api/data/{table_name}/list 接口本身就是通用的
            const res = await listTableRecords(tableName, pageSize, offset); 
            
            setTableData(res.items);
            setTotal(res.total);
            setPagination({ current: page, pageSize });
        } catch (e: any) {
            message.error(`获取表 ${tableName} 数据失败: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };
    
    // --- 操作处理 ---
    
    const handleCreate = () => {
        setModalMode('create');
        setEditingRecord(null);
        form.resetFields();
        setIsModalVisible(true);
    };

    const handleEdit = (record: any) => {
        setModalMode('edit');
        setEditingRecord(record);
        form.setFieldsValue(record);
        setIsModalVisible(true);
    };

    const handleDelete = (recordId: string) => {
        Modal.confirm({
            title: `确认删除记录?`,
            content: `ID: ${recordId}`,
            okText: '删除',
            okType: 'danger',
            cancelText: '取消',
            onOk: async () => {
                try {
                    await deleteRecord(selectedTable, recordId);
                    message.success('删除成功');
                    fetchData(pagination.current, pagination.pageSize, selectedTable);
                } catch (e: any) {
                    message.error(`删除失败: ${e.message}`);
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
                message.success('新增成功');
            } else {
                await updateCompanyRecord(editingRecord.id, values);
                message.success('更新成功');
            }

            setIsModalVisible(false);
            form.resetFields();
            fetchData(pagination.current, pagination.pageSize, selectedTable);
        } catch (e: any) {
            message.error(`操作失败: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    // --- 动态生成表格列 ---
    const columns = useMemo(() => {
        const metadata = TABLE_METADATA[selectedTable];
        if (!metadata) return [];

        const cols: any[] = metadata.fields.map(field => ({
            title: field.label,
            dataIndex: field.key,
            key: field.key,
            render: (text: any) => {
                const str = String(text || '');
                return <Tooltip title={str}>{str.length > 20 ? `${str.slice(0, 20)}...` : str}</Tooltip>;
            }
        }));

        cols.push({
            title: '操作',
            key: 'action',
            width: 150,
            render: (_: any, record: any) => (
                <Space>
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
                    <Button type="link" danger size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>删除</Button>
                </Space>
            )
        });

        return cols;
    }, [selectedTable]);

    // --- 动态生成表单项 ---
    const renderFormItems = () => {
        const metadata = TABLE_METADATA[selectedTable];
        if (!metadata) return null;
        
        return metadata.fields
            .filter(f => f.key !== 'id' && f.type !== 'datetime') // 排除ID和时间字段
            .map(field => (
                <Form.Item
                    key={field.key}
                    label={field.label}
                    name={field.key}
                    rules={[{ required: field.required, message: `请输入${field.label}` }]}
                >
                    <Input placeholder={`请输入${field.label}`} />
                </Form.Item>
            ));
    };

    return (
        <Card 
            title={<Space><DatabaseOutlined /><span>结构化数据管理</span></Space>} 
            style={{ minHeight: '80vh' }}
            extra={
                <Space>
                    <Select value={selectedTable} onChange={setSelectedTable} style={{ width: 200 }}>
                        {availableTables.map(t => <Option key={t.name} value={t.name}>{t.description}</Option>)}
                    </Select>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate} disabled={selectedTable !== 't_company'}>新增</Button>
                    <Button icon={<ReloadOutlined />} onClick={() => fetchData(pagination.current, pagination.pageSize, selectedTable)}>刷新</Button>
                </Space>
            }
        >
            {/* 提示信息 */}
            <Alert 
                message={`当前表: ${TABLE_METADATA[selectedTable]?.label || selectedTable}`} 
                description="本界面连接至 MySQL 数据库，用于管理结构化业务数据。"
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
                    onChange: (p, ps) => fetchData(p, ps, selectedTable),
                    showTotal: (t) => `共 ${t} 条`
                }}
            />

            <Modal 
                title={modalMode === 'create' ? "新增记录" : "编辑记录"} 
                open={isModalVisible} 
                onOk={handleModalOk} 
                onCancel={() => setIsModalVisible(false)} 
                confirmLoading={loading}
                destroyOnClose
            >
                <Form form={form} layout="vertical">
                    {renderFormItems()}
                </Form>
            </Modal>
        </Card>
    );
};

export default DatabaseManagementTab;