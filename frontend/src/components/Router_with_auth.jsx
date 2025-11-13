import React, { useState, useEffect } from 'react';
import AuthPage from './AuthPage';
import { useAuth } from '../contexts/AuthContext';
import ChatInterface from './ChatInterface';
import VideoUpload from './VideoUpload';
import VideoPlayer from './VideoPlayer';
import SearchResults from './SearchResults';
import VideoOutline from './VideoOutline';
import UserManagement from './UserManagement';
import { apiService } from '../services/api';

const RouterWithAuth = () => {
  const { user, loading } = useAuth();
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  
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

  // 监听路由变化
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // 确保页面占满整个视口高度
  React.useEffect(() => {
    document.documentElement.style.height = '100%'
    document.body.style.height = '100%'
    return () => {
      document.documentElement.style.height = ''
      document.body.style.height = ''
    }
  }, [])

  // 简单的导航函数
  const navigate = (path) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

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
    } else if (results && Array.isArray(results.video_info)) {
      // 处理后端返回的video_info字段
      videosData = results.video_info;
      console.log('从video_info字段获取的视频数量:', videosData.length);
    } else {
      console.log('未找到有效的视频数据字段');
    }
    
    // 确保videosData是数组
    if (!Array.isArray(videosData)) {
      console.warn('视频数据不是数组格式，重置为空数组:', videosData);
      videosData = [];
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
  const handleVideoClick = async (videoId) => {
    console.log('处理视频点击，videoId:', videoId);
    
    try {
      setIsLoading(true);
      
      // 1. 先获取视频基本信息（包含流式URL）
      console.log('正在获取视频基本信息，videoId:', videoId);
      const videoInfoResponse = await apiService.video.getVideoInfo(videoId);
      console.log('获取到的视频基本信息:', videoInfoResponse);
      
      // 2. 再获取视频大纲数据
      console.log('正在获取视频大纲，videoId:', videoId);
      const outlineResponse = await apiService.video.getOutline(videoId);
      console.log('获取到的视频大纲数据:', outlineResponse);
      
      // 3. 创建完整的视频数据对象，包含流式URL
      const completeVideoData = {
        id: videoId,
        filename: videoInfoResponse.filename,
        filePath: videoInfoResponse.filePath, // 这是流式URL
        outline: outlineResponse?.outline || null
      };
      
      console.log('完整的视频数据对象:', completeVideoData);
      
      // 设置视频数据
      setVideoData(completeVideoData);
      
      // 切换到outline视图，实现左右分栏显示（包含视频播放）
      setActiveView('outline');
      
    } catch (error) {
      console.error('处理视频点击时出错:', error);
      // 显示错误消息
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: `获取视频信息失败: ${error.message}`,
        sender: 'ai',
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  // 辅助函数：将时间字符串转换为秒数
  const convertTimeToSeconds = (timeStr) => {
    if (!timeStr || typeof timeStr !== 'string') return 0;
    
    // 处理不同格式的时间字符串
    const parts = timeStr.split(':').map(Number);
    if (parts.length === 2) {
      // MM:SS 格式
      return parts[0] * 60 + parts[1];
    } else if (parts.length === 3) {
      // HH:MM:SS 格式
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return 0;
  }

  // 处理查看视频大纲
  const handleViewOutline = async (videoData) => {
    console.log('\n=======================================');
    console.log('[用户操作] 点击视频卡片或上传完成，开始处理视频大纲和详情...');
    console.log('[输入数据] videoData:', JSON.stringify(videoData, null, 2));
    
    // 详细检查videoData中的各个可能包含ID的字段
    console.log('[ID检查] videoData.id:', videoData.id);
    console.log('[ID检查] videoData.video_id:', videoData.video_id);
    console.log('[ID检查] videoData._id:', videoData._id);
    
    const videoId = videoData.id || videoData.video_id || videoData._id;
    console.log('[最终ID] 确定的videoId:', videoId);
    
    if (!videoId) {
      console.error('❌ 视频ID不存在，无法获取大纲');
      setAppState(prev => ({ ...prev, error: '视频ID错误，无法加载大纲' }));
      return;
    }
    
    console.log(`[视频ID] ${videoId}`);
    setIsLoading(true);
    
    try {
      // ============ 步骤1: 获取视频大纲 ============
      console.log('\n[第一步] 📋 开始获取视频大纲...');
      console.log(`[第一步] 🟢 发送请求到: /v1/videos/${videoId}/outline`);
      
      const outlineStartTime = Date.now();
      const outlineData = await apiService.video.getOutline(videoId);
      const outlineEndTime = Date.now();
      
      console.log('[第一步] ✅ 视频大纲请求成功完成！');
      console.log('[第一步] ⏱️ 请求耗时:', outlineEndTime - outlineStartTime, '毫秒');
      console.log('[第一步] 📊 大纲数据:', JSON.stringify(outlineData, null, 2));
      
      // ============ 步骤2: 获取视频详情（包含播放地址） ============
      console.log('\n[第二步] 🎬 开始获取视频详情（播放地址）...');
      console.log(`[第二步] 🟢 发送请求到: /v1/videos/${videoId}`);
      
      const detailsStartTime = Date.now();
      const videoDetailsData = await apiService.video.getDetails(videoId);
      const detailsEndTime = Date.now();
      
      console.log('[第二步] ✅ 视频详情请求成功完成！');
      console.log('[第二步] ⏱️ 请求耗时:', detailsEndTime - detailsStartTime, '毫秒');
      console.log('[第二步] 📊 详情数据:', JSON.stringify(videoDetailsData, null, 2));
      
      // 验证返回的数据
      console.log('\n[数据验证] 开始验证返回的大纲和详情数据...');
      console.log('[数据验证] 大纲数据类型:', typeof outlineData);
      console.log('[数据验证] 详情数据类型:', typeof videoDetailsData);
      
      // 提取用户要求的三个字段：video_id, filename, filePath
      const extractedVideoInfo = {
        video_id: videoDetailsData.video_id || videoId,
        filename: videoDetailsData.filename || '未知文件名',
        filePath: videoDetailsData.filePath || ''  // 注意：后端现在已改为使用filePath（大写P）
      };
      
      console.log('\n[字段提取] 提取的视频详情字段:', JSON.stringify(extractedVideoInfo, null, 2));
      
      // 构建视频播放URL（根据filePath）
      let videoUrl = '';
      if (extractedVideoInfo.filePath) {
        // 如果filePath是完整URL，直接使用
        if (extractedVideoInfo.filePath.startsWith('http')) {
          videoUrl = extractedVideoInfo.filePath;
        } else {
          // 否则构建完整URL
          videoUrl = `http://localhost:8000${extractedVideoInfo.filePath}`;
        }
      }
      
      console.log('\n[URL构建] 构建的视频播放URL:', videoUrl);
      
      // 转换大纲数据格式以匹配VideoOutline组件的期望格式
      let formattedOutline = [];
      console.log('[大纲处理] 原始大纲数据:', JSON.stringify(outlineData, null, 2));
      
      // 检查大纲数据格式并进行适当的转换
      if (outlineData && outlineData.outline) {
        if (outlineData.outline.main_sections && Array.isArray(outlineData.outline.main_sections)) {
          // 格式1: { outline: { main_sections: [...] } }
          console.log('[大纲处理] 检测到格式1: 包含main_sections的大纲结构');
          formattedOutline = outlineData.outline.main_sections.map((section, index) => ({
            id: `section-${index + 1}`,
            title: section.title || `第${index + 1}节`,
            startTime: convertTimeToSeconds(section.start_time || '00:00:00'),
            endTime: convertTimeToSeconds(section.end_time || '00:00:00'),
            snippet: section.summary || '',
            children: section.subsections ? section.subsections.map((subsection, subIndex) => ({
              id: `section-${index + 1}-${subIndex + 1}`,
              title: subsection.title || `小节${subIndex + 1}`,
              startTime: convertTimeToSeconds(subsection.start_time || '00:00:00'),
              endTime: convertTimeToSeconds(subsection.end_time || '00:00:00'),
              snippet: subsection.summary || ''
            })) : []
          }));
        } else if (Array.isArray(outlineData.outline)) {
          // 格式2: { outline: [...] }
          console.log('[大纲处理] 检测到格式2: 直接是数组的大纲结构');
          formattedOutline = outlineData.outline;
        }
      } else if (Array.isArray(outlineData)) {
        // 格式3: [...] (直接是数组)
        console.log('[大纲处理] 检测到格式3: 直接是数组的大纲数据');
        formattedOutline = outlineData;
      }
      
      console.log('[大纲处理] 格式化后的大纲数据:', JSON.stringify(formattedOutline, null, 2));
      console.log('[大纲处理] 格式化后的大纲长度:', formattedOutline.length);
      
      // 准备视频数据对象
      const mergedVideoData = {
        id: videoId,
        title: videoData.title || extractedVideoInfo.filename || '未知视频',
        // 使用格式化后的大纲数据
        outline: formattedOutline,
        // 视频详情数据（只包含需要的字段）
        video: extractedVideoInfo,
        // 视频播放URL
        file: {
          url: videoUrl
        },
        // 保留原始视频信息
        originalData: videoData,
        // 网络请求统计
        requestStats: {
          outlineRequestTime: outlineEndTime - outlineStartTime,
          detailsRequestTime: detailsEndTime - detailsStartTime,
          totalRequestTime: outlineEndTime - outlineStartTime + detailsEndTime - detailsStartTime
        }
      };
      
      console.log('\n[数据合并] 合并后的视频数据:', JSON.stringify(mergedVideoData, null, 2));
      
      // 更新状态
      setVideoData(mergedVideoData);
      setActiveView('outline');
      
      console.log('\n✅ 视频大纲和详情加载完成，切换到大纲视图');
      console.log(`🎯 最终视频数据结构: videoData.outline 长度=${mergedVideoData.outline.length}`);
      console.log(`🎯 视频详情结构: videoData.video = ${JSON.stringify(mergedVideoData.video, null, 2)}`);
      console.log(`🎯 视频文件URL: ${mergedVideoData.file.url}`);
      
    } catch (error) {
      console.error('\n❌ 处理视频大纲和详情时发生错误！');
      console.error('🚨 错误对象:', error);
      console.error('🚨 错误类型:', error.constructor.name);
      
      if (error.message.includes('/outline')) {
        console.error('⚠️ 注意: 视频大纲接口错误，这可能是因为大纲数据还未生成');
      } else if (error.message.includes(`/videos/${videoId}`)) {
        console.error('⚠️ 注意: 视频详情接口错误，无法获取播放地址');
      }
      
      // 显示错误信息但仍然尝试切换到视图
      setAppState(prev => ({ ...prev, error: `加载视频信息失败: ${error.message}` }));
      
      // 即使出错也尝试切换到大纲视图，使用已有数据
      if (videoData) {
        setVideoData({ id: videoId, title: videoData.title || '未知视频', outline: [], originalData: videoData });
        setActiveView('outline');
      }
    } finally {
      setIsLoading(false);
      console.log('=======================================\n');
    }
  };

  // 处理预设问题点击
  const handlePresetClick = (question) => {
    setInputValue(question)
    // 可选：自动发送问题
    handleSend()
  }

  // 处理视频上传完成后的回调
  const handleVideoAnalyzed = (data) => {
    console.log('视频上传分析完成，准备跳转到详情页:', data);
    
    // 检查数据中是否包含有效的视频ID
    const videoId = data.id || data.video_id;
    if (!videoId) {
      console.error('警告: 上传的视频数据中没有有效的视频ID');
      setAppState(prev => ({ 
        ...prev, 
        isProcessing: false,
        error: '视频上传成功，但无法获取视频详情。请稍后刷新页面重试。'
      }));
      // 即使没有有效的ID，也设置一些基本数据以便用户可以查看
      setVideoData({
        id: 'temp-' + Date.now(), // 创建临时ID
        title: data.title || '未命名视频',
        outline: data.outline || [],
        file: data.file
      });
      setActiveView('player'); // 切换到播放器视图而不是大纲视图
      return;
    }
    
    // 只有在有有效ID的情况下才调用handleViewOutline
    handleViewOutline(data);
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
    // 切换视图到问答界面
    setActiveView('chat')
    setCurrentQuery('')
    setAppState(prev => ({ ...prev, error: null }))
    console.log('返回到问答界面')
  }

  // 清除错误
  const handleClearError = () => {
    setAppState(prev => ({ ...prev, error: null }))
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
      case 'test':
        return (
          <div className="test-page">
            <h1>认证测试页面</h1>
            {user ? (
              <div>
                <h2>欢迎, {user.username}!</h2>
                <p>邮箱: {user.email}</p>
                <p>用户ID: {user.id}</p>
                <button onClick={() => {
                  localStorage.removeItem('token');
                  window.location.reload();
                }}>登出</button>
              </div>
            ) : (
              <div>
                <h2>未登录</h2>
                <p>请先登录</p>
              </div>
            )}
          </div>
        )
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
            {/* 返回按钮 */}
            <div className="outline-header-actions">
              <button 
                className="back-button"
                onClick={handleBackToChat}
                title="返回问答界面"
              >
                ← 返回问答
              </button>
            </div>
            
            <div className="outline-content-container">
              <div className="outline-sidebar">
                <VideoOutline 
                  outline={videoData?.outline || []}
                  onItemClick={(startTime) => {
                    // 处理大纲项点击，更新视频播放位置
                    const videoElement = document.getElementById('main-video');
                    if (videoElement) {
                      videoElement.currentTime = startTime;
                      // 确保视频播放
                      if (videoElement.paused) {
                        videoElement.play();
                      }
                    }
                  }}
                  highlightSegment={videoData?.highlightSegment}
                />
              </div>
              <div className="video-player-wrapper">
                <VideoPlayer 
                  videoData={videoData}
                  autoPlay={true}
                  initialTime={videoData?.highlightSegment?.startTime || 0}
                />
              </div>
            </div>
          </div>
        )
      case 'userManagement':
        return <UserManagement onBack={() => setActiveView('chat')} />
      default:
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
    }
  }

  // 加载中状态
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>加载中...</p>
      </div>
    );
  }

  // 如果用户未登录，显示认证页面
  if (!user) {
    return <AuthPage />;
  }

  // 用户已登录，显示应用内容
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
          <button 
            className="nav-button test-btn"
            onClick={() => setActiveView('test')}
          >
            测试认证
          </button>
          <button 
            className={`nav-button user-management-btn ${activeView === 'userManagement' ? 'active' : ''}`}
            onClick={() => setActiveView('userManagement')}
          >
            用户管理
          </button>
          <button 
            className="nav-button profile-btn"
            onClick={() => navigate('/profile')}
          >
            个人资料
          </button>
          <button 
            className="nav-button logout-btn"
            onClick={() => {
              // 这里应该调用登出函数
              localStorage.removeItem('token');
              window.location.reload();
            }}
          >
            登出
          </button>
        </nav>
        
        <div className="header-info">
          {currentQuery && (
            <div className="current-query">
              搜索: <span className="query-text">{currentQuery}</span>
            </div>
          )}
          <div className="user-info">
            欢迎, {user.username}
          </div>
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
  );
};

export default RouterWithAuth;