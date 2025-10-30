import React, { useState, useRef, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import VideoUpload from './components/VideoUpload'
import VideoPlayer from './components/VideoPlayer'
import SearchResults from './components/SearchResults'
import VideoOutline from './components/VideoOutline'
import { apiService } from './services/api'

function App() {
  // 预设问题数据
  const presetQuestions = [
    '视频中讲解了哪些关键概念？',
    '请找出与React相关的片段',
    '有没有关于性能优化的内容？',
    '总结一下这个视频的主要内容'
  ]
  
  const [activeView, setActiveView] = useState('chat') // 'chat', 'upload', 'player', 'search', 'outline'
  const [searchResults, setSearchResults] = useState([])
  const [videoData, setVideoData] = useState(null)
  const [currentQuery, setCurrentQuery] = useState('')
  const [appState, setAppState] = useState({
    isProcessing: false,
    error: null
  })
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: '你好！我是QuickRewind助手，我可以帮你查找视频内容或分析你上传的视频。',
      sender: 'ai',
      timestamp: new Date().toLocaleTimeString()
    },
    {
      id: 2,
      text: '你可以直接提问查找相关视频内容，或者上传视频进行分析。',
      sender: 'ai',
      timestamp: new Date().toLocaleTimeString()
    }
  ])
  
  // 确保页面占满整个视口高度
  React.useEffect(() => {
    document.documentElement.style.height = '100%'
    document.body.style.height = '100%'
    return () => {
      document.documentElement.style.height = ''
      document.body.style.height = ''
    }
  }, [])

  // 处理聊天界面的搜索请求
  const handleSearch = async (query) => {
    // 清空之前的搜索结果
    setSearchResults([]);
    
    // 添加用户消息到聊天界面
    setMessages(prev => [...prev, {
      id: Date.now(),
      text: query,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString()
    }]);
    
    try {
      // 显示加载状态
      setIsLoading(true);
      
      // 调用真实的API获取搜索结果
      console.log('开始调用API搜索视频:', query);
      const results = await apiService.video.search(query);
      console.log('API返回的搜索结果:', JSON.stringify(results));
      
      // 格式化搜索结果并添加到聊天
      formatSearchResultsForChat(results, query);
      
    } catch (error) {
      console.error('搜索失败:', error);
      
      // 错误处理：创建一个错误消息
      const errorMessage = {
        id: Date.now(),
        text: `搜索过程中出现错误: ${error.message}`,
        sender: 'ai',
        timestamp: new Date().toLocaleTimeString(),
        videoResults: []
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  // 格式化搜索结果并添加到聊天界面
  const formatSearchResultsForChat = (results, query) => {
    console.log('formatSearchResultsForChat - 输入结果:', JSON.stringify(results));
    
    // 从响应中提取视频数据
    let videosData = [];
    if (results && Array.isArray(results.videos)) {
      videosData = results.videos;
      console.log('从videos字段获取的视频数量:', videosData.length);
    } else if (Array.isArray(results)) {
      // 兼容数组格式的返回结果
      videosData = results;
      console.log('直接使用数组格式的结果，数量:', videosData.length);
    } else if (results && Array.isArray(results.results)) {
      videosData = results.results;
      console.log('从results字段获取的视频数量:', videosData.length);
    } else {
      console.log('未找到有效的视频数据字段');
    }
    
    // 获取消息文本
    const messageText = results?.message || `未找到与'${query}'相关的视频结果`;
    console.log('消息文本:', messageText);
    console.log('准备添加到videoResults的数据:', JSON.stringify(videosData));
    
    // 创建AI消息对象，确保videoResults字段正确设置
    const aiMessage = {
      id: Date.now(),
      text: messageText,
      sender: 'ai',
      timestamp: new Date().toLocaleTimeString(),
      // 直接使用视频数据作为videoResults字段
      videoResults: videosData
    };
    
    console.log('创建的AI消息对象:', JSON.stringify(aiMessage));
    
    // 直接更新messages状态
    setMessages(prev => {
      const newMessages = [...prev, aiMessage];
      console.log('更新后的消息列表长度:', newMessages.length);
      console.log('最后一条消息的videoResults:', JSON.stringify(newMessages[newMessages.length-1].videoResults));
      return newMessages;
    });
    
    // 保存结果以便后续可能使用
    setSearchResults(videosData);
  }

  // 处理视频链接点击
  const handleVideoClick = (videoId) => {
    console.log('处理视频点击，videoId:', videoId);
    // 先从搜索结果中查找视频
    let video = searchResults.find(v => v.id === videoId);
    
    // 如果没找到，尝试从所有消息中查找包含这个videoId的视频结果
    if (!video) {
      console.log('在searchResults中未找到，尝试从消息历史中查找');
      for (const msg of messages) {
        if (msg.videoResults && Array.isArray(msg.videoResults)) {
          const foundVideo = msg.videoResults.find(v => v.id === videoId);
          if (foundVideo) {
            video = foundVideo;
            break;
          }
        }
      }
    }
    
    // 如果找到视频，设置数据并切换视图
    if (video) {
      console.log('找到视频数据:', video);
      setVideoData(video);
      setActiveView('player');
    } else {
      console.error('未找到ID为', videoId, '的视频');
    }
  }

  // 处理查看大纲按钮点击
  const handleViewOutline = (videoData) => {
    setVideoData(videoData);
    setActiveView('outline');
  }

  // 处理预设问题点击
  const handlePresetClick = (question) => {
    setInputValue(question)
    // 可选：自动发送问题
    handleSend()
  }

  // 处理视频上传完成后的回调
  const handleVideoAnalyzed = (data) => {
    setVideoData(data)
    setActiveView('player')
    setAppState(prev => ({ ...prev, isProcessing: false }))
  }

  // 处理搜索结果选择
  const handleResultSelect = (video) => {
    setVideoData(video)
    setActiveView('player')
  }

  // 处理上传开始
  const handleUploadStart = () => {
    setActiveView('upload')
    setAppState(prev => ({ ...prev, isProcessing: true, error: null }))
  }

  // 返回聊天界面
  const handleBackToChat = () => {
    setActiveView('chat')
    setCurrentQuery('')
    setAppState(prev => ({ ...prev, error: null }))
  }

  // 清除错误
  const handleClearError = () => {
    setAppState(prev => ({ ...prev, error: null }))
  }

  // 生成模拟搜索结果
  const generateMockSearchResults = (query) => {
    const mockVideos = [
      { 
        id: '1', 
        title: 'React入门教程 - 基础概念详解',
        relevance: 95,
        similarity: 95,
        matchedSubtitles: '这是一个关于React基础概念的详细讲解，包括组件、状态和属性等核心知识点。',
        matched_subtitles: '这是一个关于React基础概念的详细讲解，包括组件、状态和属性等核心知识点。',
        snippet: 'React基础概念详解',
        thumbnail: 'https://picsum.photos/400/225?random=1',
        timestamp: '02:15',
        duration: '12:45',
        keywords: ['React', '基础概念', '组件', '状态']
      },
      { 
        id: '2', 
        title: 'React Hooks完全指南',
        relevance: 88,
        similarity: 88,
        matchedSubtitles: '在这个视频中，我们将深入探讨React Hooks的使用方法和最佳实践。',
        matched_subtitles: '在这个视频中，我们将深入探讨React Hooks的使用方法和最佳实践。',
        snippet: 'React Hooks使用详解',
        thumbnail: 'https://picsum.photos/400/225?random=2',
        timestamp: '01:30',
        duration: '08:22',
        keywords: ['React', 'Hooks', '状态管理']
      },
      { 
        id: '3', 
        title: 'React性能优化技巧',
        relevance: 82,
        similarity: 82,
        matchedSubtitles: '学习如何通过代码分割、懒加载和其他技术来优化React应用的性能。',
        matched_subtitles: '学习如何通过代码分割、懒加载和其他技术来优化React应用的性能。',
        snippet: 'React应用性能优化',
        thumbnail: 'https://picsum.photos/400/225?random=3',
        timestamp: '03:45',
        duration: '15:30',
        keywords: ['React', '性能优化', '代码分割']
      },
      { 
        id: '4', 
        title: 'React与Redux结合使用',
        relevance: 75,
        similarity: 75,
        matchedSubtitles: '本教程将介绍如何在React应用中集成Redux进行状态管理。',
        matched_subtitles: '本教程将介绍如何在React应用中集成Redux进行状态管理。',
        snippet: 'React与Redux集成',
        thumbnail: 'https://picsum.photos/400/225?random=4',
        timestamp: '05:20',
        duration: '18:15',
        keywords: ['React', 'Redux', '状态管理']
      },
      { 
        id: '5', 
        title: 'React路由配置详解',
        relevance: 70,
        similarity: 70,
        matchedSubtitles: '学习如何使用React Router进行前端路由管理和页面导航。',
        matched_subtitles: '学习如何使用React Router进行前端路由管理和页面导航。',
        snippet: 'React Router使用指南',
        thumbnail: 'https://picsum.photos/400/225?random=5',
        timestamp: '08:10',
        duration: '22:40',
        keywords: ['React', 'Router', '路由']
      }
    ];
    
    console.log('生成的模拟视频数据:', mockVideos); // 添加调试信息
    return mockVideos;
  }

  // 生成AI响应
  const generateResponse = async (userQuery) => {
    // 添加用户消息到聊天界面
    setMessages(prev => [...prev, {
      id: Date.now(),
      text: userQuery,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString()
    }]);
    
    // 显示加载状态
    setIsLoading(true);
    
    try {
      // 添加特殊关键词测试，当用户输入"测试视频卡片"时直接生成模拟视频结果
      if (userQuery.toLowerCase().includes('测试视频卡片')) {
        console.log('执行视频卡片测试');
        // 直接生成模拟数据并显示视频卡片
        const mockResults = generateMockSearchResults('React教程');
        // 确保mockResults中包含matchedSubtitles字段
        mockResults.forEach((video, index) => {
          video.matchedSubtitles = `这是第${index + 1}个视频的匹配字幕内容，包含了与查询相关的关键信息。`;
        });
        formatSearchResultsForChat(mockResults, 'React教程');
        return;
      }
      
      // 调用Agent API获取智能回复
      const apiResponse = await apiService.agent.sendMessage(userQuery);
      
      // 提取回答内容和视频信息，处理不同响应格式
      let responseContent = '';
      let videoResults = [];
      
      if (typeof apiResponse === 'object' && apiResponse !== null) {
        // 提取文本响应
        responseContent = apiResponse.response || apiResponse.message || JSON.stringify(apiResponse);
        
        // 提取视频信息
        if (apiResponse.video_info && Array.isArray(apiResponse.video_info)) {
          // 将后端的video_info格式转换为前端需要的格式
          videoResults = apiResponse.video_info.map(video => ({
            id: video.video_id || String(Math.random()),
            title: video.title || '未命名视频',
            relevance: video.relevance_score || 75,
            similarity: video.relevance_score || 75,
            matchedSubtitles: `与"${userQuery}"相关的视频内容`,
            matched_subtitles: `与"${userQuery}"相关的视频内容`,
            timestamp: video.timestamp || '',
            thumbnail: video.thumbnail || '',
            snippet: video.title || '',
            duration: '00:00'
          }));
          console.log('从API响应中提取的视频信息:', videoResults);
        }
      } else {
        responseContent = String(apiResponse);
      }
      
      // 判断是否需要直接进行视频搜索
      const isSearchQuery = 
        userQuery.toLowerCase().includes('查找') || 
        userQuery.toLowerCase().includes('搜索') || 
        userQuery.toLowerCase().includes('find') || 
        userQuery.toLowerCase().includes('search');
      
      // 如果是搜索查询，直接调用handleSearch进行视频搜索
      // 否则，添加AI的回答到聊天，包括可能的视频结果
      if (isSearchQuery) {
        await handleSearch(userQuery);
      } else {
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: responseContent,
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString(),
          videoResults: videoResults // 添加视频结果到消息对象
        }]);
      }
    } catch (error) {
      console.error('AI响应生成失败:', error);
      
      // 失败时使用本地逻辑生成响应
      let fallbackResponse = '';
      if (userQuery.toLowerCase().includes('你好') || userQuery.toLowerCase().includes('hello')) {
        fallbackResponse = '您好！很高兴为您服务。您想查找什么类型的视频内容，或者需要我分析某个视频吗？';
      } else if (userQuery.toLowerCase().includes('帮助') || userQuery.toLowerCase().includes('help')) {
        fallbackResponse = `我可以帮您：\n1. 基于您的问题查找相关视频内容\n2. 分析您上传的视频并生成大纲\n3. 帮助您快速定位视频中的重要片段\n\n请告诉我您想做什么。`;
      } else if (userQuery.toLowerCase().includes('查找') || userQuery.toLowerCase().includes('搜索') || 
                 userQuery.toLowerCase().includes('find') || userQuery.toLowerCase().includes('search')) {
        // 触发搜索
        await handleSearch(userQuery);
      } else {
        fallbackResponse = `感谢您的问题！关于"${userQuery}"，我需要更多信息才能提供完整答案。您是想了解这方面的视频内容，还是有其他相关问题？`;
      }
      
      // 如果有回退响应，添加到聊天
      if (fallbackResponse) {
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: fallbackResponse,
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } finally {
      setIsLoading(false);
    }
  }
  
  // 处理发送按钮点击
  const handleSend = () => {
    if (!inputValue.trim()) return;
    
    // 保存输入内容并清空
    const query = inputValue.trim();
    setInputValue('');
    
    // 调用生成AI响应的函数
    generateResponse(query);
  }

  // 处理Enter键发送
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 渲染内容区域
  const renderContent = () => {
    switch (activeView) {
      case 'chat':
        console.log('渲染ChatInterface组件，消息数据:', messages); // 添加调试信息
        return (
          <ChatInterface 
            onSearch={handleSearch}
            onUploadClick={handleUploadStart}
            messages={messages}
            isLoading={isLoading}
            onPresetClick={handlePresetClick}
            onVideoClick={handleVideoClick}
            onViewOutline={handleViewOutline}
            onResultSelect={handleResultSelect}
          />
        )
      case 'upload':
        return (
          <VideoUpload 
            onVideoAnalyzed={handleVideoAnalyzed}
            isProcessing={appState.isProcessing}
          />
        )
      case 'player':
        return (
          <VideoPlayer videoData={videoData} />
        )
      case 'search':
        return (
          <SearchResults 
            results={searchResults}
            onResultSelect={handleResultSelect}
            onViewOutline={handleViewOutline}
          />
        )
      case 'outline':
        return (
          <div className="outline-view">
            <div className="outline-sidebar">
              <VideoOutline 
                outline={videoData?.outline || []}
                onItemClick={(startTime) => {
                  // 处理大纲项点击，更新视频播放位置
                  const videoElement = document.getElementById('main-video');
                  if (videoElement) {
                    videoElement.currentTime = startTime;
                  }
                }}
                highlightSegment={videoData?.highlightSegment}
              />
            </div>
            <div className="video-player-container">
              <VideoPlayer 
                videoData={videoData}
                autoPlay={true}
                initialTime={videoData?.highlightSegment?.startTime || 0}
              />
            </div>
          </div>
        )
      default:
        return <ChatInterface onSearch={handleSearch} onUploadClick={handleUploadStart} />
    }
  }

  return (
    <div className="app" style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      margin: 0, 
      padding: 0
    }}>
      {/* 顶部导航栏 */}
      <header className="app-header">
        <div className="app-logo">
          <h1>QuickRewind</h1>
          <span className="subtitle">智能视频分析助手</span>
        </div>
        
        <nav className="app-nav">
          <button 
            className={`nav-button chat-btn ${activeView === 'chat' ? 'active' : ''}`}
            onClick={handleBackToChat}
          >
            对话
          </button>
          <button 
            className={`nav-button upload-btn ${activeView === 'upload' ? 'active' : ''}`}
            onClick={handleUploadStart}
          >
            上传视频
          </button>
        </nav>
        
        <div className="header-info">
          {currentQuery && (
            <div className="current-query">
              搜索: <span className="query-text">{currentQuery}</span>
            </div>
          )}
        </div>
      </header>

      {/* 主要内容区域 */}
      <div className="app-content">
        {appState.error && (
          <div className="error-alert">
            <span className="error-message">{appState.error}</span>
            <button className="error-close" onClick={handleClearError}>×</button>
          </div>
        )}
        
        <div className="content-container" style={{ flex: 1, marginBottom: 0, paddingBottom: 0 }}>
          {renderContent()}
        </div>
      </div>

      {/* 底部区域：聊天输入框和页脚 */}
      <div className="app-bottom-container">
        {/* 预设问题区域 */}
        {activeView === 'chat' && (
          <div className="preset-questions">
            <span className="preset-label">快速提问:</span>
            <div className="preset-buttons">
              {presetQuestions.map((question, index) => (
                <button
                  key={index}
                  className="preset-button"
                  onClick={() => handlePresetClick(question)}
                  disabled={isLoading}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* 聊天输入容器 */}
        {activeView === 'chat' && (
          <div className="chat-input-container">
            <textarea
              className="chat-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入您的问题..."
              rows="2"
              disabled={isLoading}
            />
            <button 
              className="send-button"
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
            >
              {isLoading ? '发送中...' : '发送'}
            </button>
          </div>
        )}

        {/* 底部状态栏 */}
        <footer className="app-footer">
          <div className="footer-info" style={{ 
            margin: 0, 
            padding: 0 
          }}>
            <div className="status-indicator">
              <span className={appState.isProcessing ? 'processing' : ''}></span>
              <span>{appState.isProcessing ? '处理中...' : '就绪'}</span>
            </div>
          </div>
          <div className="copyright">© 2024 QuickRewind</div>
        </footer>
      </div>
    </div>
  )
}

export default App
