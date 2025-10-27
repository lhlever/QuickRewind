import { useRef, useEffect } from 'react'
import './ChatInterface.css'

const ChatInterface = ({ onSearch, messages = [], isLoading = false, onUploadClick, onPresetClick, onVideoClick }) => {
  const chatContainerRef = useRef(null)
  const lastMessageRef = useRef(null)

  // 直接滚动到底部的函数
  const scrollToBottom = () => {
    if (lastMessageRef.current) {
      // 使用scrollIntoView确保最新消息可见，设置block为'nearest'以避免不必要的滚动
      lastMessageRef.current.scrollIntoView({ block: 'end', behavior: 'smooth' })
    } else if (chatContainerRef.current) {
      // 备用方案：直接操作scrollTop属性
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }

  // 使用requestAnimationFrame确保在下一帧执行滚动
  const scheduleScroll = () => {
    window.requestAnimationFrame(() => {
      scrollToBottom()
    })
  }

  // 当消息变化时执行滚动
  useEffect(() => {
    scheduleScroll()
  }, [messages])

  // 当加载状态变化时也执行滚动
  useEffect(() => {
    scheduleScroll()
  }, [isLoading])

  // 监听DOM变化，确保内容更新后滚动到底部
  useEffect(() => {
    const observer = new MutationObserver(() => {
      scheduleScroll()
    })
    
    if (chatContainerRef.current) {
      observer.observe(chatContainerRef.current, {
        childList: true,
        subtree: true
      })
    }
    
    return () => observer.disconnect()
  }, [])

  // 处理预设问题点击
  const handlePresetClick = (question) => {
    if (onPresetClick) {
      onPresetClick(question)
    }
  }

  // 处理消息容器内的点击事件，捕获视频链接点击
  const handleMessageClick = (e) => {
    // 检查是否点击了视频链接
    if (e.target.classList.contains('video-link') && onVideoClick) {
      e.preventDefault(); // 阻止默认链接行为
      const videoId = e.target.dataset.videoId;
      if (videoId) {
        onVideoClick(videoId);
      }
    }
  };

  // 格式化消息文本，支持Markdown和视频链接
  const formatMessage = (text) => {
    if (!text) return '';
    
    // 首先处理视频链接格式: [视频链接:id]标题[/视频链接]
    let formattedText = text.replace(/\[视频链接:(\d+)\]([^\[]*)\[\/视频链接\]/g, 
      '<a href="#" class="video-link" data-video-id="$1">$2</a>'
    );
    
    // 然后处理Markdown粗体格式: **文本**
    formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // 处理换行符
    formattedText = formattedText.replace(/\n/g, '<br>');
    
    return formattedText;
  };

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

      <div 
        className="chat-container" 
        ref={chatContainerRef}
        onClick={handleMessageClick}
      >
        {messages.map((message, index) => {
          // 为最后一条消息添加ref
          const isLastMessage = index === messages.length - 1;
          
          return (
            <div 
              key={message.id} 
              className={`message ${message.sender}`}
            >
              <div className="message-content">
                <div 
                  className="message-text"
                  ref={isLastMessage ? lastMessageRef : null}
                  dangerouslySetInnerHTML={{ __html: formatMessage(message.text) }}
                ></div>
                <div className="message-meta">
                  <span className="message-time">{message.timestamp}</span>
                </div>
              </div>
            </div>
          );
        })}

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