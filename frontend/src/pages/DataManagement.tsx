import React, { useState } from 'react';
import { Tabs, Typography } from 'antd';
import { DatabaseOutlined, ReadOutlined } from '@ant-design/icons';
import KnowledgeBaseTab from '../components/KnowledgeBaseTab'; // 导入重命名后的知识库组件
import DatabaseManagementTab from '../components/DatabaseManagementTab'; // 导入结构化数据管理组件

const { Title } = Typography;

const DataManagement: React.FC = () => {
    
    const items = [
        {
            key: 'database',
            label: (
                <span>
                    <DatabaseOutlined /> 结构化数据管理
                </span>
            ),
            children: <DatabaseManagementTab />,
        },
        {
            key: 'knowledge',
            label: (
                <span>
                    <ReadOutlined /> 知识库管理 (RAG)
                </span>
            ),
            children: <KnowledgeBaseTab />,
        },
    ];

    return (
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: 0 }}>
            <Title level={2} style={{ textAlign: 'center', marginBottom: 24 }}>
                <DatabaseOutlined /> 企业数据管理中心
            </Title>
            <Tabs 
                defaultActiveKey="database" 
                items={items} 
                size="large"
                tabPosition='top'
                centered
            />
        </div>
    );
};

export default DataManagement;