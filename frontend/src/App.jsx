import { useState } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import VideoUpload from './components/VideoUpload'
import VideoPlayer from './components/VideoPlayer'
import SearchResults from './components/SearchResults'

function App() {
  const [activeView, setActiveView] = useState('chat') // 'chat', 'upload', 'player', 'search'
  const [searchResults, setSearchResults] = useState([])
  const [videoData, setVideoData] = useState(null)
  const [currentQuery, setCurrentQuery] = useState('')
  const [appState, setAppState] = useState({
    isProcessing: false,
    error: null
  })

  // 处理聊天界面的搜索请求
  const handleSearch = (query) => {
    setCurrentQuery(query)
    setActiveView('search')
    
    // 模拟搜索结果
    const mockResults = generateMockSearchResults(query)
    setSearchResults(mockResults)
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

  // 渲染内容区域
  const renderContent = () => {
    switch (activeView) {
      case 'chat':
        return (
          <ChatInterface 
            onSearch={handleSearch}
            onUploadClick={handleUploadStart}
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
    <div className="app">
      {/* 顶部导航栏 */}
      <header className="app-header">
        <div className="app-logo">
          <h1>QuickRewind</h1>
          <span className="subtitle">智能视频分析助手</span>
        </div>
        
        <nav className="app-nav">
          <button 
            className={`nav-button ${activeView === 'chat' ? 'active' : ''}`}
            onClick={handleBackToChat}
          >
            对话
          </button>
          <button 
            className={`nav-button ${activeView === 'upload' ? 'active' : ''}`}
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
      <main className="app-main">
        {appState.error && (
          <div className="error-alert">
            <span className="error-message">{appState.error}</span>
            <button className="error-close" onClick={handleClearError}>×</button>
          </div>
        )}
        
        <div className="content-container">
          {renderContent()}
        </div>
      </main>

      {/* 底部状态栏 */}
      <footer className="app-footer">
        <div className="footer-info">
          QuickRewind © 2024 | 智能视频分析平台
        </div>
        
        <div className="status-indicator">
          {appState.isProcessing ? (
            <span className="processing">处理中...</span>
          ) : (
            <span className="online">在线</span>
          )}
        </div>
      </footer>
    </div>
  )
}

export default App
