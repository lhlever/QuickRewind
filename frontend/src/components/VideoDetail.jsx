import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import VideoPlayer from './VideoPlayer';
import VideoOutline from './VideoOutline';
import './VideoDetail.css';

const VideoDetail = ({ videoId, onBack }) => {
  const [videoData, setVideoData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [outlineData, setOutlineData] = useState([]);

  // 加载视频详情数据
  useEffect(() => {
    const loadVideoDetail = async () => {
      if (!videoId) return;
      
      try {
        setIsLoading(true);
        setError(null);
        
        console.log('开始加载视频详情，videoId:', videoId);
        
        // 并行获取视频详情和大纲数据
        const [detailsResponse, outlineResponse] = await Promise.all([
          apiService.video.getDetails(videoId),
          apiService.video.getOutline(videoId)
        ]);
        
        console.log('视频详情数据:', detailsResponse);
        console.log('视频大纲数据:', outlineResponse);
        
        // 构建完整的视频数据对象
        const completeVideoData = {
          id: videoId,
          title: detailsResponse.title || detailsResponse.filename || '未知标题',
          filename: detailsResponse.filename,
          filePath: detailsResponse.filePath,
          hls_playlist: detailsResponse.hls_playlist,
          duration: detailsResponse.duration,
          file_size: detailsResponse.file_size,
          status: detailsResponse.status,
          created_at: detailsResponse.created_at,
          updated_at: detailsResponse.updated_at,
          thumbnail: detailsResponse.thumbnail_url,
          outline: outlineResponse?.outline || []
        };
        
        setVideoData(completeVideoData);
        setOutlineData(outlineResponse?.outline || []);
        
      } catch (err) {
        console.error('加载视频详情失败:', err);
        setError('加载视频详情失败，请稍后重试');
      } finally {
        setIsLoading(false);
      }
    };

    loadVideoDetail();
  }, [videoId]);

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (!bytes) return '未知';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 格式化时长
  const formatDuration = (seconds) => {
    if (!seconds) return '未知';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}小时${minutes}分钟${secs}秒`;
    } else {
      return `${minutes}分钟${secs}秒`;
    }
  };

  // 格式化日期
  const formatDate = (dateString) => {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 获取状态标签
  const getStatusLabel = (status) => {
    const statusMap = {
      'uploaded': '已上传',
      'processing': '处理中',
      'completed': '已完成',
      'failed': '处理失败'
    };
    return statusMap[status] || status;
  };

  // 获取状态样式类名
  const getStatusClass = (status) => {
    return `status-${status}`;
  };

  if (isLoading) {
    return (
      <div className="video-detail">
        <div className="video-detail-header">
          <button className="back-button" onClick={onBack}>
            ← 返回
          </button>
          <h2>视频详情</h2>
        </div>
        <div className="video-detail-loading">
          <div className="loading-spinner"></div>
          <p>正在加载视频详情...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-detail">
        <div className="video-detail-header">
          <button className="back-button" onClick={onBack}>
            ← 返回
          </button>
          <h2>视频详情</h2>
        </div>
        <div className="video-detail-error">
          <p>{error}</p>
          <button className="retry-button" onClick={() => window.location.reload()}>
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!videoData) {
    return (
      <div className="video-detail">
        <div className="video-detail-header">
          <button className="back-button" onClick={onBack}>
            ← 返回
          </button>
          <h2>视频详情</h2>
        </div>
        <div className="video-detail-error">
          <p>未找到视频数据</p>
        </div>
      </div>
    );
  }

  return (
    <div className="video-detail">
      {/* 头部 */}
      <div className="video-detail-header">
        <button className="back-button" onClick={onBack}>
          ← 返回
        </button>
        <div className="header-content">
          <h2>{videoData.title}</h2>
          <div className="video-meta-info">
            <span className={`status-badge ${getStatusClass(videoData.status)}`}>
              {getStatusLabel(videoData.status)}
            </span>
            <span className="meta-item">时长: {formatDuration(videoData.duration)}</span>
            <span className="meta-item">大小: {formatFileSize(videoData.file_size)}</span>
            <span className="meta-item">上传: {formatDate(videoData.created_at)}</span>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="video-detail-content">
        {/* 视频播放器 */}
        <div className="video-player-section">
          <div className="section-header">
            <h3>视频播放</h3>
          </div>
          <div className="player-container">
            <VideoPlayer 
              videoData={videoData}
              autoPlay={true}
            />
          </div>
        </div>

        {/* 视频大纲 */}
        {outlineData.length > 0 && (
          <div className="outline-section">
            <div className="section-header">
              <h3>视频大纲</h3>
              <span className="outline-count">{outlineData.length} 个章节</span>
            </div>
            <div className="outline-container">
              <VideoOutline 
                outline={outlineData}
                onItemClick={(startTime) => {
                  // 处理大纲项点击，跳转到对应时间点
                  const videoElement = document.querySelector('video');
                  if (videoElement) {
                    videoElement.currentTime = startTime;
                    videoElement.play();
                  }
                }}
              />
            </div>
          </div>
        )}

        {/* 视频信息 */}
        <div className="info-section">
          <div className="section-header">
            <h3>视频信息</h3>
          </div>
          <div className="info-grid">
            <div className="info-item">
              <label>文件名:</label>
              <span>{videoData.filename}</span>
            </div>
            <div className="info-item">
              <label>视频ID:</label>
              <span>{videoData.id}</span>
            </div>
            <div className="info-item">
              <label>时长:</label>
              <span>{formatDuration(videoData.duration)}</span>
            </div>
            <div className="info-item">
              <label>文件大小:</label>
              <span>{formatFileSize(videoData.file_size)}</span>
            </div>
            <div className="info-item">
              <label>上传时间:</label>
              <span>{formatDate(videoData.created_at)}</span>
            </div>
            <div className="info-item">
              <label>最后更新:</label>
              <span>{formatDate(videoData.updated_at)}</span>
            </div>
            <div className="info-item">
              <label>处理状态:</label>
              <span className={`status-text ${getStatusClass(videoData.status)}`}>
                {getStatusLabel(videoData.status)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoDetail;