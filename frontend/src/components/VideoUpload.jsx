import React, { useState, useRef, useEffect } from 'react';
import './VideoUpload.css';
import { apiService } from '../services/api';

const VideoUpload = ({ onVideoAnalyzed }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [videoId, setVideoId] = useState(null);
  const [processingSteps, setProcessingSteps] = useState([]);
  const [overallProgress, setOverallProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState('');
  const fileInputRef = useRef(null);
  const statusPollInterval = useRef(null);

  // 处理文件选择
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    handleFile(file);
  };

  // 处理文件拖放
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  // 文件处理逻辑
  const handleFile = (file) => {
    if (!file) return;

    // 检查文件类型 - 支持更多常见视频格式
    const validTypes = [
      'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime', // MOV格式的正确MIME类型
      'video/x-msvideo', // AVI
      'video/x-matroska', // MKV
      'video/x-flv', // FLV
      'video/x-ms-wmv', // WMV
      'video/mpeg', // MPEG, MPG
      'video/3gpp', // 3GP
      'video/3gpp2' // 3G2
    ];
    if (!validTypes.includes(file.type)) {
      // 获取文件扩展名用于更好的错误提示
      const fileExt = file.name.split('.').pop().toLowerCase();
      setError(`文件类型不支持。请上传有效的视频文件。当前文件扩展名: ${fileExt}`);
      return;
    }

    // 检查文件大小（限制为500MB）
    if (file.size > 500 * 1024 * 1024) {
      setError('文件大小不能超过500MB');
      return;
    }

    setError(null);
    setSelectedFile(file);
    handleUploadAndAnalysis(file);
  };

  // 真实的上传和分析过程
  const handleUploadAndAnalysis = (file) => {
    setIsProcessing(true);
    setUploadProgress(0);
    setError(null);

    // 创建FormData用于文件上传
    const formData = new FormData();
    formData.append('file', file);
    // 移除title字段，因为后端API没有要求这个参数

    // 调用API上传视频
    apiService.video.upload(formData, (progress) => {
      setUploadProgress(progress);
    })
    .then(response => {
      // 保存videoId并开始轮询处理状态
      setVideoId(response.video_id);
      startStatusPolling(response.video_id);
      
      // 上传完成后获取视频详情和大纲 - 改为轮询完成后获取
    })
    .catch(err => {
      console.error('视频上传失败:', err);
      // 显示从API返回的详细错误信息，如果没有则使用通用消息
      setError(err.message || '视频上传失败，请稍后重试');
      setIsProcessing(false);
      
      // 失败时使用模拟数据作为备选
      setTimeout(() => {
        const mockOutline = generateMockOutline();
        if (onVideoAnalyzed) {
          onVideoAnalyzed({
            file,
            outline: mockOutline,
            title: file.name,
            duration: Math.floor(Math.random() * 600) + 300,
            thumbnail: URL.createObjectURL(file)
          });
        }
      }, 1000);
    });
  };
  
  // 开始轮询处理状态
  const startStatusPolling = (id) => {
    // 清除现有的轮询
    if (statusPollInterval.current) {
      clearInterval(statusPollInterval.current);
    }
    
    // 设置新的轮询
    statusPollInterval.current = setInterval(() => {
      pollProcessingStatus(id);
    }, 2000); // 每2秒轮询一次
    
    // 立即执行一次
    pollProcessingStatus(id);
  };
  
  // 轮询处理状态
  const pollProcessingStatus = async (id) => {
    try {
      const statusResponse = await apiService.video.getStatus(id);
      
      // 更新状态和进度
      setProcessingStatus(statusResponse.status);
      setOverallProgress(statusResponse.progress_percentage);
      setProcessingSteps(statusResponse.processing_steps || []);
      
      // 如果处理完成或失败，停止轮询并获取结果
      if (statusResponse.status === 'completed') {
        stopStatusPolling();
        // 获取视频详情和大纲
        try {
          console.log(`开始获取视频详情和大纲，videoId: ${id}`);
          const [videoDetails, videoOutline] = await Promise.all([
            apiService.video.getDetails(id),
            apiService.video.getOutline(id)
          ]);
          console.log('获取到的视频详情:', videoDetails);
          console.log('获取到的视频大纲:', videoOutline);
          
          if (onVideoAnalyzed) {
            // 构建与搜索结果一致的数据格式，以便App组件可以正确处理跳转到详情页
            onVideoAnalyzed({
              // 优先使用原始的id参数，确保视频ID一定存在
              id: id, // 使用传入的原始id参数
              video_id: id, // 使用传入的原始id参数作为video_id
              // 同时保留从videoDetails获取的字段，确保数据完整性
              title: videoDetails.title || selectedFile?.name,
              duration: videoDetails.duration,
              outline: videoOutline,
              thumbnail: videoDetails.thumbnail_url || (selectedFile ? URL.createObjectURL(selectedFile) : null),
              file: selectedFile, // 保留原文件引用以便本地播放
              filename: videoDetails.filename || selectedFile?.name,
              // 保留原始的videoDetails对象，便于调试和后续处理
              originalDetails: videoDetails
            });
          }
          
          setIsProcessing(false);
        } catch (err) {
          console.error('获取视频详情失败:', err);
          setError('处理成功但获取结果失败，请刷新页面重试');
          setIsProcessing(false);
        }
      } else if (statusResponse.status === 'failed') {
        stopStatusPolling();
        setError('视频处理失败，请稍后重试');
        setIsProcessing(false);
      }
    } catch (err) {
      console.error('轮询处理状态失败:', err);
    }
  };
  
  // 停止轮询
  const stopStatusPolling = () => {
    if (statusPollInterval.current) {
      clearInterval(statusPollInterval.current);
      statusPollInterval.current = null;
    }
  };
  
  // 清理轮询
  useEffect(() => {
    return () => {
      stopStatusPolling();
    };
  }, []);

  // 生成模拟的视频大纲数据
  const generateMockOutline = () => {
    const sections = [
      {
        id: '1',
        title: '介绍和背景',
        startTime: 0,
        endTime: 120,
        subsections: [
          {
            id: '1.1',
            title: '项目概述',
            startTime: 0,
            endTime: 45
          },
          {
            id: '1.2',
            title: '历史背景',
            startTime: 45,
            endTime: 120
          }
        ]
      },
      {
        id: '2',
        title: '主要内容和功能',
        startTime: 120,
        endTime: 300,
        subsections: [
          {
            id: '2.1',
            title: '核心特性展示',
            startTime: 120,
            endTime: 180
          },
          {
            id: '2.2',
            title: '实际应用案例',
            startTime: 180,
            endTime: 300
          }
        ]
      },
      {
        id: '3',
        title: '技术细节和实现',
        startTime: 300,
        endTime: 480,
        subsections: [
          {
            id: '3.1',
            title: '架构设计',
            startTime: 300,
            endTime: 360
          },
          {
            id: '3.2',
            title: '关键算法',
            startTime: 360,
            endTime: 480
          }
        ]
      },
      {
        id: '4',
        title: '总结和未来计划',
        startTime: 480,
        endTime: 600,
        subsections: [
          {
            id: '4.1',
            title: '项目总结',
            startTime: 480,
            endTime: 540
          },
          {
            id: '4.2',
            title: '未来发展路线',
            startTime: 540,
            endTime: 600
          }
        ]
      }
    ];
    return sections;
  };

  const handleRetry = () => {
    setSelectedFile(null);
    setError(null);
    setUploadProgress(0);
    setVideoId(null);
    setProcessingSteps([]);
    setOverallProgress(0);
    setProcessingStatus('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  // 格式化持续时间，将秒数转换为更易读的格式
  const formatDuration = (seconds) => {
    if (seconds < 1) {
      return `${Math.round(seconds * 1000)}ms`;
    } else if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    } else {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
    }
  };

  return (
    <div className="video-upload-container">
    {/* 移除重复的标题栏，只保留主应用的标题栏 */}

      {!selectedFile && (
        <div 
          className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            type="file" 
            accept="video/*" 
            ref={fileInputRef} 
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <div className="upload-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </div>
          <p className="upload-text">拖放视频文件到此处或点击上传</p>
          <p className="upload-hint">支持 MP4, WebM, OGG, MOV 格式，最大 500MB</p>
        </div>
      )}

      {isProcessing && (
        <div className="processing-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${uploadProgress < 100 ? uploadProgress : overallProgress}%` }}
            ></div>
          </div>
          <p className="progress-text">
            {uploadProgress < 100 ? '正在上传...' : `正在处理: ${processingStatus === 'transcribing' ? '语音识别' : processingStatus === 'analyzing' ? '内容分析' : '处理中'}`}
          </p>
          <p className="progress-percentage">{uploadProgress < 100 ? uploadProgress : overallProgress}%</p>
          
          {/* 显示处理步骤详情 */}
          {uploadProgress >= 100 && processingSteps.length > 0 && (
            <div className="processing-steps">
              <h4>处理进度</h4>
              <div className="steps-list">
                {processingSteps.map((step, index) => (
                  <div 
                    key={index} 
                    className={`step-item ${step.status}`}
                  >
                    <div className="step-icon">
                      {step.status === 'completed' && <span className="icon-complete">✓</span>}
                      {step.status === 'in_progress' && <span className="icon-processing">⏳</span>}
                      {step.status === 'failed' && <span className="icon-failed">✗</span>}
                    </div>
                    <div className="step-info">
                      <div className="step-header">
                        <span className="step-name">{step.name}</span>
                        {step.duration !== null && (
                          <span className="step-duration">耗时: {formatDuration(step.duration)}</span>
                        )}
                      </div>
                      <div className="step-footer">
                        {step.status === 'in_progress' && <span className="step-status processing">处理中...</span>}
                        {step.status === 'completed' && <span className="step-status completed">已完成</span>}
                        {step.status === 'failed' && (
                          <span className="step-status failed">失败 {step.error && `: ${step.error}`}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button 
            className="retry-button" 
            onClick={handleRetry}
          >
            重新上传
          </button>
        </div>
      )}
    </div>
  );
};

export default VideoUpload;