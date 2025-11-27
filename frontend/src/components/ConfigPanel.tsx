import React, { useEffect } from 'react'; 
import { Card, Form, Input, Select, Button, message, Typography } from 'antd';
import useAppState from '../hooks/useAppState';
import { saveConfig } from '../services/api';

const { Paragraph } = Typography;

const ConfigPanel: React.FC = () => {
    const { state, setState } = useAppState();
    const [form] = Form.useForm();

    const supportedModels = [
        { name: 'GPT-4o', value: 'gpt-4o' },
        { name: 'GPT-4 Turbo', value: 'gpt-4-turbo' },
        { name: 'Claude 3 Opus', value: 'claude-3-opus' },
        { name: 'Gemini 2.5 Pro', value: 'gemini-2.5-pro' },
    ];

    useEffect(() => {
        form.setFieldsValue(state.config);
    }, [state.config, form]);

    const onFinish = async (values: any) => {
        try {
            await saveConfig(values);
            setState({ config: values });
            message.success('配置更新成功！');
        } catch (error) {
            message.error(`配置更新失败: ${error}`);
        }
    };

    return (
        <div>
            <Paragraph type="secondary">
                您可以在此切换底层 AI 模型，并配置必要的 API Key。
            </Paragraph>

            <Form
                form={form}
                layout="vertical"
                initialValues={state.config}
                onFinish={onFinish}
            >
                <Form.Item
                    name="modelName"
                    label="AI 模型选择"
                    rules={[{ required: true, message: '请选择一个 AI 模型!' }]}
                >
                    <Select
                        placeholder="选择 AI 模型"
                        options={supportedModels.map(model => ({
                            label: model.name,
                            value: model.value,
                        }))}
                    />
                </Form.Item>

                <Form.Item
                    name="apiKey"
                    label="API Key"
                    tooltip="用于访问所选 AI 模型的密钥"
                    rules={[{ required: true, message: '请输入 API Key!' }]}
                >
                    <Input.Password placeholder="请输入您的 API Key" />
                </Form.Item>

                <Form.Item>
                    <Button type="primary" htmlType="submit">
                        保存配置
                    </Button>
                </Form.Item>
            </Form>
        </div>
    );
};

export default ConfigPanel;
