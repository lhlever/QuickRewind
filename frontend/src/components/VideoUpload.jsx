import React, { useState, useRef } from 'react';
import './VideoUpload.css';

const VideoUpload = ({ onVideoAnalyzed }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

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

    // 检查文件类型
    const validTypes = ['video/mp4', 'video/webm', 'video/ogg', 'video/mov'];
    if (!validTypes.includes(file.type)) {
      setError('请上传有效的视频文件（MP4, WebM, OGG, MOV）');
      return;
    }

    // 检查文件大小（限制为500MB）
    if (file.size > 500 * 1024 * 1024) {
      setError('文件大小不能超过500MB');
      return;
    }

    setError(null);
    setSelectedFile(file);
    simulateUploadAndAnalysis(file);
  };

  // 模拟上传和分析过程
  const simulateUploadAndAnalysis = (file) => {
    setIsProcessing(true);
    setUploadProgress(0);

    // 模拟上传进度
    let progress = 0;
    const uploadInterval = setInterval(() => {
      progress += 5;
      setUploadProgress(progress);
      if (progress >= 100) {
        clearInterval(uploadInterval);
        
        // 模拟分析过程
        setTimeout(() => {
          // 生成模拟的视频大纲数据
          const mockOutline = generateMockOutline();
          
          if (onVideoAnalyzed) {
            onVideoAnalyzed({
              file,
              outline: mockOutline,
              title: file.name,
              duration: Math.floor(Math.random() * 600) + 300, // 5-15分钟的随机时长
              thumbnail: URL.createObjectURL(file) // 在实际应用中，应该使用生成的缩略图
            });
          }
          
          setIsProcessing(false);
        }, 3000);
      }
    }, 200);
  };

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

  // 重新上传
  const handleRetry = () => {
    setSelectedFile(null);
    setError(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <p className="progress-text">
            {uploadProgress < 100 ? '正在上传...' : '正在分析视频...'}
          </p>
          <p className="progress-percentage">{uploadProgress}%</p>
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