import { useState, useRef, useEffect } from 'react'
import './ChatInterface.css'

const ChatInterface = ({ onSearch }) => {
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
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const chatContainerRef = useRef(null)

  // 自动滚动到底部
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])

  // 处理发送消息
  const handleSend = () => {
    if (!inputValue.trim()) return

    // 添加用户消息
    const newMessage = {
      id: Date.now(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString()
    }
    
    setMessages([...messages, newMessage])
    setInputValue('')
    setIsLoading(true)

    // 模拟AI思考和回复延迟
    setTimeout(() => {
      generateResponse(inputValue)
    }, 1000)
  }

  // 生成AI响应
  const generateResponse = (userQuery) => {
    let response = ''
    let shouldTriggerSearch = false
    
    // 根据用户输入生成不同的响应
    if (userQuery.toLowerCase().includes('你好') || userQuery.toLowerCase().includes('hello')) {
      response = '您好！很高兴为您服务。您想查找什么类型的视频内容，或者需要我分析某个视频吗？'
    } else if (userQuery.toLowerCase().includes('帮助') || userQuery.toLowerCase().includes('help')) {
      response = `我可以帮您：
1. 基于您的问题查找相关视频内容
2. 分析您上传的视频并生成大纲
3. 帮助您快速定位视频中的重要片段

请告诉我您想做什么。`
    } else if (userQuery.toLowerCase().includes('查找') || userQuery.toLowerCase().includes('搜索') || 
               userQuery.toLowerCase().includes('find') || userQuery.toLowerCase().includes('search')) {
      // 触发搜索
      response = `我正在搜索与"${userQuery}"相关的视频...`
      shouldTriggerSearch = true
    } else if (userQuery.toLowerCase().includes('上传') || userQuery.toLowerCase().includes('upload')) {
      response = '您可以在顶部切换到"上传"标签来上传视频文件，我会为您分析并生成视频大纲。'
    } else {
      // 默认响应
      response = `我理解您想了解关于"${userQuery}"的内容。让我为您查找相关的视频...`
      shouldTriggerSearch = true
    }
    
    // 添加AI回复
    setMessages(prev => [...prev, {
      id: Date.now(),
      text: response,
      sender: 'ai',
      timestamp: new Date().toLocaleTimeString()
    }])
    setIsLoading(false)
    
    // 如果需要，触发搜索
    if (shouldTriggerSearch && onSearch) {
      setTimeout(() => {
        onSearch(userQuery)
        // 添加搜索结果通知
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          text: `已找到几个与您查询相关的视频，您可以在右侧预览并点击查看详情。`,
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString()
        }])
      }, 1500)
    }
  }

  // 处理Enter键发送
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 预设问题
  const presetQuestions = [
    '视频中讲解了哪些关键概念？',
    '请找出与React相关的片段',
    '有没有关于性能优化的内容？',
    '总结一下这个视频的主要内容'
  ]

  // 处理预设问题点击
  const handlePresetClick = (question) => {
    setInputValue(question)
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="header-content">
          <h3>QuickRewind 助手</h3>
          <div className="online-status">
            <span className="status-dot"></span>
            <span className="status-text">在线</span>
          </div>
        </div>
        <p>通过自然语言提问查找视频内容</p>
      </div>

      <div className="chat-container" ref={chatContainerRef}>
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`message ${message.sender}`}
          >
            <div className="message-content">
              {message.text}
              <span className="message-time">{message.timestamp}</span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message ai loading">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>

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
    </div>
  )
}

export default ChatInterface