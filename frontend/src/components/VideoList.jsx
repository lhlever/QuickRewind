import React, { useState, useEffect } from 'react';
import './VideoList.css';
import { apiService } from '../services/api';

const VideoList = ({ onVideoClick, onViewDetail, activeVideoId }) => {
  const [videos, setVideos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // 加载用户视频列表
  useEffect(() => {
    const loadUserVideos = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const videoList = await apiService.video.getUserVideos();
        console.log('获取到的用户视频列表:', videoList);
        
        // 添加更详细的调试日志
        if (videoList && videoList.length > 0) {
//           console.log('视频列表类型:', typeof videoList);
//           console.log('视频列表是否为数组:', Array.isArray(videoList));
//           console.log('第一个视频对象结构:', JSON.stringify(videoList[0], null, 2));
//           console.log('第一个视频的所有属性:', Object.keys(videoList[0]));
//           console.log('第一个视频的ID字段:', videoList[0].id, videoList[0]._id, videoList[0].video_id);
          
          // 遍历所有视频，检查ID字段
          videoList.forEach((video, index) => {
            console.log(`视频${index + 1}的ID字段:`, {
              id: video.id,
              _id: video._id,
              video_id: video.video_id,
              title: video.title
            });
          });
        }
        
        setVideos(videoList);
      } catch (err) {
        console.error('加载用户视频列表失败:', err);
        setError('加载视频列表失败，请稍后重试');
      } finally {
        setIsLoading(false);
      }
    };

    loadUserVideos();
  }, []);

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
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
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
  };

  // 格式化日期
  const formatDate = (dateString) => {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="video-list">
        <div className="video-list-header">
          <h3>我的视频</h3>
        </div>
        <div className="video-list-loading">
          <div className="loading-spinner"></div>
          <p>正在加载视频列表...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-list">
        <div className="video-list-header">
          <h3>我的视频</h3>
        </div>
        <div className="video-list-error">
          <p>{error}</p>
          <button 
            className="retry-button"
            onClick={() => window.location.reload()}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="video-list">
      <div className="video-list-header">
        <h3>我的视频</h3>
        <span className="video-count">{videos.length} 个视频</span>
      </div>
      
      <div className="video-list-content">
        {videos.length === 0 ? (
          <div className="no-videos">
            <div className="no-videos-icon">🎬</div>
            <p>暂无上传的视频</p>
            <p className="no-videos-hint">上传视频后，它们将显示在这里</p>
          </div>
        ) : (
          <div className="video-items">
            {videos.map((video) => (
              <div
                key={video.id || video._id || video.video_id}
                className={`video-item ${activeVideoId === (video.id || video._id || video.video_id) ? 'active' : ''}`}
                onClick={() => onVideoClick(video)}
                title="点击查看视频"
              >
                <div className="video-thumbnail">
                  <div className="video-icon">🎬</div>
                </div>
                
                <div className="video-info">
                  <h4 className="video-title">{video.title}</h4>
                  
                  <div className="video-meta">
                    <div className="meta-item">
                      <span className="meta-label">时长:</span>
                      <span className="meta-value">{formatDuration(video.duration)}</span>
                    </div>
                    
                    <div className="meta-item">
                      <span className="meta-label">大小:</span>
                      <span className="meta-value">{formatFileSize(video.file_size)}</span>
                    </div>
                    
                    <div className="meta-item">
                      <span className="meta-label">上传:</span>
                      <span className="meta-value">{formatDate(video.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoList;