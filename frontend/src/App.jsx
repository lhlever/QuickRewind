import React, { useState, useRef, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import VideoUpload from './components/VideoUpload'
import VideoPlayer from './components/VideoPlayer'
import SearchResults from './components/SearchResults'
import { apiService } from './services/api'

function App() {
  // 预设问题数据
  const presetQuestions = [
    '视频中讲解了哪些关键概念？',
    '请找出与React相关的片段',
    '有没有关于性能优化的内容？',
    '总结一下这个视频的主要内容'
  ]
  
  const [activeView, setActiveView] = useState('chat') // 'chat', 'upload', 'player', 'search'
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
      
      // 调用API获取搜索结果
      const results = await apiService.video.search(query);
      
      // 格式化搜索结果并添加到聊天
      formatSearchResultsForChat(results, query);
      
    } catch (error) {
      console.error('搜索失败:', error);
      
      // 使用模拟数据
      const mockResults = generateMockSearchResults(query);
      formatSearchResultsForChat(mockResults, query);
    } finally {
      setIsLoading(false);
    }
  }

  // 将搜索结果格式化为聊天消息
  const formatSearchResultsForChat = (results, query) => {
    // 确保results是数组格式
    const resultsArray = Array.isArray(results) ? results : [];
    
    if (resultsArray.length === 0) {
      // 没有找到结果
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: `没有找到与"${query}"相关的视频内容。`,
        sender: 'ai',
        timestamp: new Date().toLocaleTimeString(),
        videoResults: [] // 空结果数组
      }]);
      return;
    }
    
    // 格式化搜索结果消息
    let searchResultsMessage = `我找到了 ${resultsArray.length} 个与"${query}"相关的视频：\n\n`;
    
    // 创建带有视频ID的特殊标记，后续在ChatInterface中处理为链接
    resultsArray.slice(0, 3).forEach((video, index) => {
      // 使用特殊格式标记视频标题，包含视频ID
      const videoLink = `[视频链接:${video.id}]${video.title}[/视频链接]`;
      searchResultsMessage += `${index + 1}. **${videoLink}**\n`;
      searchResultsMessage += `   时长: ${video.duration}\n`;
      searchResultsMessage += `   简介: ${video.snippet.substring(0, 100)}${video.snippet.length > 100 ? '...' : ''}\n\n`;
    });
    
    if (resultsArray.length > 3) {
      searchResultsMessage += `还有 ${resultsArray.length - 3} 个结果未显示...`;
    }
    
    // 添加到聊天消息，同时保存实际的结果对象便于后续处理
    setMessages(prev => [...prev, {
      id: Date.now(),
      text: searchResultsMessage,
      sender: 'ai',
      timestamp: new Date().toLocaleTimeString(),
      videoResults: resultsArray // 保存实际的视频结果数据
    }]);
    
    // 保存结果以便后续可能使用
    setSearchResults(resultsArray);
  }

  // 处理视频链接点击
  const handleVideoClick = (videoId) => {
    // 从保存的搜索结果中找到对应的视频
    const video = searchResults.find(v => v.id === videoId);
    if (video) {
      setVideoData(video);
      setActiveView('player');
    }
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
    // 根据查询生成相关的模拟搜索结果
    return [
      {
        id: '1',
        title: `如何有效${query} - 专业指南`,
        snippet: `这是一个关于如何有效${query}的详细教程，包含实用技巧和步骤说明。通过本视频，您将学习到${query}的核心方法和最佳实践。`,
        thumbnail: 'https://picsum.photos/400/225?random=1',
        timestamp: '02:15',
        duration: '12:45',
        relevance: 98,
        keywords: ['指南', '教程', query, '最佳实践']
      },
      {
        id: '2',
        title: `专业人士分享${query}技巧`,
        snippet: `资深专家分享${query}的实用技巧，帮助您快速掌握核心技能。通过实际案例演示，让学习更加直观有效。`,
        thumbnail: 'https://picsum.photos/400/225?random=2',
        timestamp: '01:30',
        duration: '08:22',
        relevance: 92,
        keywords: [query, '技巧', '专家分享', '案例演示']
      },
      {
        id: '3',
        title: `${query}的最新趋势与创新`,
        snippet: `探索${query}领域的最新趋势和创新方法，了解行业前沿发展动态，为您的工作和学习提供新的思路和方向。`,
        thumbnail: 'https://picsum.photos/400/225?random=3',
        timestamp: '03:45',
        duration: '15:30',
        relevance: 87,
        keywords: [query, '趋势', '创新', '前沿技术']
      },
      {
        id: '4',
        title: `${query}实战演练与常见问题解答`,
        snippet: `通过实战演练展示${query}的完整流程，同时解答初学者常见的问题和困惑，帮助您避免常见陷阱。`,
        thumbnail: 'https://picsum.photos/400/225?random=4',
        timestamp: '05:20',
        duration: '18:15',
        relevance: 84,
        keywords: [query, '实战', '常见问题', '初学者指南']
      },
      {
        id: '5',
        title: `${query}专家访谈：行业洞察与建议`,
        snippet: `独家访谈${query}领域的顶级专家，获取第一手的行业洞察和专业建议，提升您的知识水平和实践能力。`,
        thumbnail: 'https://picsum.photos/400/225?random=5',
        timestamp: '08:10',
        duration: '22:40',
        relevance: 80,
        keywords: [query, '专家访谈', '行业洞察', '专业建议']
      }
    ]
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
      
      // 提取回答内容，处理可能的不同响应格式
      let responseContent = '';
      if (typeof apiResponse === 'object' && apiResponse !== null) {
        responseContent = apiResponse.response || apiResponse.message || JSON.stringify(apiResponse);
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
      // 否则，添加AI的普通回答到聊天
      if (isSearchQuery) {
        await handleSearch(userQuery);
      } else {
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: responseContent,
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString()
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
        return (
          <ChatInterface 
            onSearch={handleSearch}
            onUploadClick={handleUploadStart}
            messages={messages}
            isLoading={isLoading}
            onPresetClick={handlePresetClick}
            onVideoClick={handleVideoClick}
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
          />
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
