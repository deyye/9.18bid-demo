import React, { useState } from 'react';
import { Button, Upload, message, Spin, Typography, Space, Input, UploadFile } from 'antd';
import { Card as AntCard } from 'antd';
import { UploadOutlined, FileTextOutlined, SendOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { RcFile } from 'antd/es/upload';
import useAppState from '../hooks/useAppState';
import { uploadDocument, analyzeDocument, analyzeDocumentStream } from '../services/api';
import { AppState, ProcessStep } from '../types';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

interface DocumentAnalysisProps {
    onNext: () => void;
}

const DocumentAnalysis: React.FC<DocumentAnalysisProps> = ({ onNext }) => {
    const { state, setState } = useAppState();
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [uploading, setUploading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    
    // 存储后端返回的文件ID
    const [uploadedFileId, setUploadedFileId] = useState<string | null>(null);

    // 文件上传处理 (仅管理文件列表，阻止默认上传)
    const handleUpload = (file: RcFile) => {
        // 可以在这里限制文件类型和大小
        // 修复 TS2739: 强制将 RcFile 断言为 UploadFile，因为我们是在手动管理 fileList
        setFileList([file as unknown as UploadFile]);
        return false; // 阻止自动上传
    };

    // 移除文件并清空状态
    const handleRemove = () => {
        setFileList([]);
        setUploadedFileId(null);
        
        setState({ documentContent: '', overview: '', requirements: '' });
    };

    // 步骤 1: 上传文件并请求后端提取文本
    const startUploadAndExtract = async () => {
        if (fileList.length === 0) {
            message.error('请先选择招标文件!');
            return;
        }

        setUploading(true);
        // 这里需要将其转回 RcFile 以发送给后端，因为我们知道存进去的就是 RcFile
        const file = fileList[0] as unknown as RcFile;
        
        // 清空旧的分析结果
        setState({ documentContent: '', overview: '', requirements: '' });

        try {
            message.info(`正在上传文件：${file.name} 并提取文本内容...`);
            
            // 调用 api.ts 中的 uploadDocument 函数
            const response = await uploadDocument(file);
            
            // ⚠️ 关键假设：uploadDocument 成功后，后端返回了提取的文本内容
            const extractedContent = response.file_content || ''; 
            
            if (!extractedContent) {
                 message.warning("后端返回的文本内容为空，可能是扫描件或解析失败");
            }

            setUploadedFileId(response.fileId || null); 
            
            setState({ documentContent: extractedContent });
            
            message.success(`文件上传成功，内容已提取。`);
        } catch (error: any) {
            console.error(error);
            message.error(`文件处理失败: ${error.message || '未知错误'}`);
            handleRemove(); // 失败后清理
        } finally {
            setUploading(false);
        }
    };

    // 步骤 2: 文档分析（调用 AI）
    const startAnalysis = async () => {
        if (!state.documentContent) {
            message.warning('文件内容提取失败，无法开始分析。');
            return;
        }

        setAnalyzing(true);
        // 清空之前的结果
        setState({ ...state, overview: '', requirements: '' });

        try {
            message.info('AI 正在并行分析项目概述和技术要求...');

            // 定义两个 Promise 同时执行
            const task1 = analyzeDocumentStream(
                state.documentContent,
                'overview',
                (chunk) => {
                    // 实时更新 overview
                    setState((prev: AppState) => ({
                        ...prev,
                        overview: (prev.overview || '') + chunk
                    }));
                },
                (err) => message.error(`项目概述分析出错: ${err}`)
            );

            const task2 = analyzeDocumentStream(
                state.documentContent,
                'requirements',
                (chunk) => {
                    // 实时更新 requirements
                    setState((prev: AppState) => ({
                        ...prev,
                        requirements: (prev.requirements || '') + chunk
                    }));
                },
                (err) => message.error(`技术要求分析出错: ${err}`)
            );

            // 等待两个任务都完成（无论成功失败）
            await Promise.allSettled([task1, task2]);
            
            message.success('文档双向分析完成！');
            // 更新当前步骤状态
            setState((prev: AppState) => ({ ...prev, currentStep: ProcessStep.DOCUMENT_ANALYSIS }));

        } catch (error: any) {
            console.error(error);
            message.error('分析过程发生异常');
        } finally {
            setAnalyzing(false);
        }
    };
    
    // 步骤 3: 下一步
    const handleNext = () => {
        // 检查两个字段是否有内容
        if (state.overview && state.requirements) {
            onNext(); 
        } else {
            message.warning('请等待分析完成（需包含项目概述和技术要求）。');
        }
    };
    
    const isReadyForAnalysis = state.documentContent !== '' && !analyzing;
    const isAnalysisDone = state.analysisResult !== '';

    return (
        <AntCard title="智能文档解析" style={{ minHeight: '80vh' }}>
            <Spin spinning={uploading || analyzing} tip={uploading ? "文件处理中..." : "AI 正在分析..."}>
                <Title level={4}>1. 上传招标文件</Title>
                <Paragraph>请上传 Word 或 PDF 格式的招标文件，系统将自动提取文本内容。</Paragraph>

                <Space style={{ marginBottom: 24, alignItems: 'flex-start' }}>
                    <Upload
                        beforeUpload={handleUpload}
                        fileList={fileList}
                        onRemove={handleRemove}
                        maxCount={1}
                        accept=".doc,.docx,.pdf,.txt"
                    >
                        <Button icon={<UploadOutlined />} disabled={fileList.length > 0 || uploading}>
                            选择文件
                        </Button>
                    </Upload>
                    {fileList.length > 0 && (
                        <Button 
                            type="primary" 
                            onClick={startUploadAndExtract} 
                            disabled={state.documentContent !== '' || uploading}
                            loading={uploading}
                        >
                            <FileTextOutlined /> 提取内容
                        </Button>
                    )}
                    {fileList.length > 0 && (
                        <Button 
                            danger
                            onClick={handleRemove} 
                            icon={<CloseCircleOutlined />} 
                            disabled={uploading || analyzing}
                        >
                            移除文件
                        </Button>
                    )}
                </Space>

                <Title level={4}>2. 提取内容预览</Title>
                <TextArea
                    rows={10}
                    placeholder="招标文件提取的原文将显示在这里..."
                    value={state.documentContent}
                    readOnly
                    style={{ marginBottom: 16 }}
                />

                <Button 
                    icon={<FileTextOutlined />} 
                    type="primary" 
                    onClick={startAnalysis} 
                    disabled={!isReadyForAnalysis || isAnalysisDone}
                    loading={analyzing}
                >
                    开始 AI 分析
                </Button>

                <Title level={4} style={{ marginTop: 24 }}>3. AI 分析结果</Title>
                <div style={{ display: 'flex', gap: '16px', marginBottom: 24 }}>
                <div style={{ flex: 1 }}>
                    <Title level={5}>项目概述 (Overview)</Title>
                    <TextArea
                        rows={10}
                        placeholder="AI 正在生成项目概述..."
                        value={state.overview} // 绑定 overview
                        readOnly
                        style={{ backgroundColor: '#fafafa', resize: 'none' }}
                    />
                </div>
                <div style={{ flex: 1 }}>
                    <Title level={5}>技术评分要求 (Requirements)</Title>
                    <TextArea
                        rows={10}
                        placeholder="AI 正在提取评分标准..."
                        value={state.requirements} // 绑定 requirements
                        readOnly
                        style={{ backgroundColor: '#fafafa', resize: 'none' }}
                    />
                </div>
            </div>
            
            <div style={{ textAlign: 'right' }}>
                <Button 
                    type="primary" 
                    onClick={handleNext} 
                    disabled={!state.overview || !state.requirements} 
                    icon={<SendOutlined />}
                >
                    下一步：AI生成目录
                </Button>
            </div>
        </Spin>
    </AntCard>
    );
};

export default DocumentAnalysis;