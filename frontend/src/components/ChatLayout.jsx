import React, { useState } from 'react';
import ChatInterface from './ChatInterface';
import VideoList from './VideoList';
import './ChatLayout.css';

const ChatLayout = ({ 
  onSearch, 
  messages = [], 
  isLoading = false, 
  onUploadClick, 
  onPresetClick, 
  onVideoClick, 
  onViewOutline,
  onViewDetail,
  inputValue,
  onInputChange,
  onSend
}) => {
  const [activeVideoId, setActiveVideoId] = useState(null);
  const [isVideoListVisible, setIsVideoListVisible] = useState(true);

  // 处理视频点击
  const handleVideoClick = (video) => {
    console.log('点击视频:', video);
    console.log('视频对象类型:', typeof video);
    console.log('视频对象的所有属性:', Object.keys(video));
    console.log('视频ID:', video.id);
    console.log('视频_id:', video.video_id);
    console.log('视频_id:', video._id);
    
    // 确定视频ID
    const videoId = video.id || video.video_id || video._id;
    console.log('最终确定的视频ID:', videoId);
    
    if (videoId) {
      setActiveVideoId(videoId);
    }
    
    // 优先使用onViewOutline回调，因为它包含完整的大纲和播放功能
    if (onViewOutline) {
      console.log('调用onViewOutline，传入完整的视频对象');
      onViewOutline(video);
    } else if (onVideoClick) {
      console.log('调用onVideoClick，传入视频ID');
      onVideoClick(videoId);
    }
  };

  // 切换视频列表显示状态
  const toggleVideoList = () => {
    setIsVideoListVisible(!isVideoListVisible);
  };

  return (
    <div className="chat-layout">
      {/* 左侧视频列表 */}
      {isVideoListVisible && (
        <div className="chat-layout-sidebar">
          <VideoList 
            onVideoClick={handleVideoClick}
            onViewDetail={onViewDetail}
            activeVideoId={activeVideoId}
          />
        </div>
      )}
      
      {/* 主聊天区域 */}
      <div className="chat-layout-main">
        {/* 顶部工具栏 */}
        <div className="chat-layout-toolbar">
          <button 
            className="toggle-video-list-btn"
            onClick={toggleVideoList}
            title={isVideoListVisible ? '隐藏视频列表' : '显示视频列表'}
          >
            {isVideoListVisible ? '◀' : '▶'}
          </button>
          
          <div className="chat-layout-title">
            <h2>视频对话助手</h2>
            <p>与AI助手交流，探索您的视频内容</p>
          </div>
        </div>
        
        {/* 聊天界面 */}
        <div className="chat-layout-content">
          <ChatInterface
            onSearch={onSearch}
            messages={messages}
            isLoading={isLoading}
            onUploadClick={onUploadClick}
            onPresetClick={onPresetClick}
            onVideoClick={onVideoClick}
            onViewOutline={onViewOutline}
            inputValue={inputValue}
            onInputChange={onInputChange}
            onSend={onSend}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatLayout;