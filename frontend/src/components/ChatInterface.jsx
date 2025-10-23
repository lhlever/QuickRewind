import { useRef, useEffect } from 'react'
import './ChatInterface.css'

const ChatInterface = ({ onSearch, messages = [], isLoading = false, onUploadClick, onPresetClick }) => {
  const chatContainerRef = useRef(null)

  // 自动滚动到底部
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])

  // 处理预设问题点击
  const handlePresetClick = (question) => {
    if (onPresetClick) {
      onPresetClick(question)
    }
  }

  // 预设问题
  const presetQuestions = [
    '视频中讲解了哪些关键概念？',
    '请找出与React相关的片段',
    '有没有关于性能优化的内容？',
    '总结一下这个视频的主要内容'
  ]

  return (
    <div className="chat-interface">
      {/* 移除重复的标题栏，只保留主应用的标题栏 */}

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


    </div>
  )
}

export default ChatInterface