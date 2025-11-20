import { useRef, useEffect, useState } from 'react'
import './ChatInterface.css'

// 测试代码 - 确认文件已加载
console.log('✅✅✅ ChatInterface.jsx 已加载！时间:', new Date().toLocaleTimeString());

const ChatInterface = ({
  onSearch,
  messages = [],
  isLoading = false,
  onUploadClick,
  onPresetClick,
  onVideoClick,
  onViewOutline,
  inputValue: externalInputValue,
  onInputChange,
  onSend
}) => {
//   console.log('🔵 ChatInterface 组件渲染，onSend:', typeof onSend);


  const chatContainerRef = useRef(null)
  const lastMessageRef = useRef(null)
  const [internalInputValue, setInternalInputValue] = useState('')
  
  // 支持受控和非受控模式
  const inputValue = externalInputValue !== undefined ? externalInputValue : internalInputValue
  const setInputValue = onInputChange || setInternalInputValue

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

  // 处理输入框变化
  const handleInputChange = (e) => {
    setInputValue(e.target.value)
  }

  // 处理发送消息
  const handleSendMessage = () => {
    console.log('🎯🎯🎯 [ChatInterface] handleSendMessage 被调用！');
    console.log('[ChatInterface] inputValue:', inputValue);
    console.log('[ChatInterface] isLoading:', isLoading);
    console.log('[ChatInterface] onSend存在吗:', !!onSend);

    if (inputValue.trim() && !isLoading) {
      const message = inputValue.trim();
      console.log('[ChatInterface] 准备发送消息:', message);

      // 先清空输入框
      setInputValue('');

      if (onSend) {
        console.log('[ChatInterface] 调用 onSend，消息:', message);
        onSend(message);
      } else if (onSearch) {
        console.log('[ChatInterface] 调用 onSearch，消息:', message);
        onSearch(message);
      }
    } else {
      console.log('[ChatInterface] 不发送消息，原因: inputValue为空或正在加载');
    }
  }

  // 处理Enter键发送
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // 处理消息容器内的点击事件，捕获视频链接和视频卡片点击
  const handleMessageClick = (e) => {
    // 检查是否点击了视频链接
    if (e.target.classList.contains('video-link') && onVideoClick) {
      e.preventDefault(); // 阻止默认链接行为
      const videoId = e.target.dataset.videoId;
      if (videoId) {
        onVideoClick(videoId);
      }
    }
    // 检查是否点击了视频卡片或卡片内的任何元素
    else {
      const videoCard = e.target.closest('.video-card');
      if (videoCard) {
        const videoId = videoCard.dataset.videoId;
        const videoData = findVideoDataById(videoId);
        if (videoId && videoData) {
          // 优先使用onViewOutline处理视频卡片点击
          if (onViewOutline) {
            console.log('点击了视频卡片，调用onViewOutline，videoData:', videoData);
            onViewOutline(videoData);
          } else if (onVideoClick) {
            console.log('点击了视频卡片，调用onVideoClick，videoId:', videoId);
            onVideoClick(videoId);
          }
        }
      }
    }
  };
  
  // 根据视频ID查找完整的视频数据
  const findVideoDataById = (videoId) => {
    // 遍历所有消息中的videoResults
    for (const message of messages) {
      if (message.videoResults && Array.isArray(message.videoResults)) {
        const foundVideo = message.videoResults.find(v => (v.id === videoId || v.video_id === videoId));
        if (foundVideo) {
          return foundVideo;
        }
      }
    }
    return null;
  };

  // 格式化消息文本，处理视频链接和Markdown格式
  const formatMessage = (text, videoResults = []) => {
//     console.log('formatMessage - 接收到的videoResults:', videoResults);
//     console.log('formatMessage - videoResults类型:', typeof videoResults);
//     console.log('formatMessage - videoResults是否为数组:', Array.isArray(videoResults));
//     console.log('formatMessage - videoResults长度:', Array.isArray(videoResults) ? videoResults.length : 'N/A');
    
    // 确保text是字符串类型
    const messageText = typeof text === 'string' ? text : String(text || '');
    
    // 确保videoResults是数组
    const validVideoResults = Array.isArray(videoResults) ? videoResults : [];
//     console.log('formatMessage - 处理后的有效视频结果数量:', validVideoResults.length);
    
    // 为视频卡片创建HTML模板
      const createVideoCard = (videoData) => {
        console.log('createVideoCard - 接收到的视频数据:', videoData);
        try {
          // 确保videoData对象存在且为有效对象
          if (!videoData || typeof videoData !== 'object') {
            console.warn('无效的视频数据对象:', videoData);
            return '';
          }
          
          // 安全地获取视频数据，提供默认值和范围检查
          const videoId = videoData.id || videoData.video_id || Date.now().toString();
          const title = videoData.title || '未知视频标题';
          const relevance = Math.max(0, Math.min(100, videoData.relevance !== undefined ? videoData.relevance : (videoData.similarity || (videoData.relevance_score || 75))));
          const matchedSubtitles = videoData.matchedSubtitles || videoData.matched_subtitles || videoData.snippet || '暂无匹配内容信息';
          const thumbnail = videoData.thumbnail || '';
          
          console.log('createVideoCard - 处理后的视频数据:', {
            videoId,
            title,
            relevance,
            matchedSubtitles,
            thumbnail
          });
          
          // 创建相关性标签
          const relevanceBadge = `<div class="video-card-relevance">${relevance}%</div>`;
          
          // 创建字幕部分
          const subtitleSection = `
            <div class="video-card-subtitles">
              <div class="subtitle-label">匹配内容:</div>
              <div class="subtitle-text">${matchedSubtitles}</div>
            </div>`;
          
          // 创建缩略图部分
          const thumbnailSection = thumbnail ? 
            `<img src="${thumbnail}" alt="${title}" class="video-thumbnail-image" />` : 
            `<div class="placeholder-thumbnail"><span class="video-icon">🎬</span></div>`;
          
          return `
            <div class="video-card-container">
              <div class="video-card" data-video-id="${videoId}">
                <div class="video-card-thumbnail">
                  ${thumbnailSection}
                  ${relevanceBadge}
                </div>
                <div class="video-card-content">
                  <h4 class="video-card-title">${title}</h4>
                  ${subtitleSection}
                </div>
              </div>
            </div>
          `;
        } catch (error) {
          console.error('创建视频卡片时出错:', error);
          // 返回一个基本的错误卡片
          return `
            <div class="video-card-container">
              <div class="video-card" data-video-id="error-${Date.now()}">
                <div class="video-card-content">
                  <h4 class="video-card-title">视频信息加载出错</h4>
                </div>
              </div>
            </div>
          `;
        }
    };
    
    // 使用传入的视频结果创建卡片
    let videoCardsHTML = '';
    if (validVideoResults.length > 0) {
      // 使用实际的视频数据创建卡片，最多显示3个
      videoCardsHTML = validVideoResults.slice(0, 3).map(video => createVideoCard(video)).join('');
    }
    
    // 转换文本格式（简单的Markdown支持）
    let formattedText = messageText || '';
    formattedText = formattedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formattedText = formattedText.replace(/\n/g, '<br>');
    
    // 返回完整的HTML，包括文本和视频卡片
    return `
      <div class="message-content">
        <div class="text-content">${formattedText}</div>
        <div class="video-cards-wrapper">${videoCardsHTML}</div>
      </div>
    `;
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
//           console.log("--------");
//           console.log(message);
//           console.log("--------");
//           // 详细调试信息
//           console.log(`处理消息 ${index} (ID: ${message.id})`, {
//             text: message.text,
//             sender: message.sender,
//             hasVideoResults: message.videoResults && message.videoResults.length > 0,
//             videoResultsType: typeof message.videoResults,
//             videoResultsLength: Array.isArray(message.videoResults) ? message.videoResults.length : '非数组'
//           });
          
          // 处理视频结果，增强容错能力
          let safeVideoResults = [];
          
          // 检查message.videoResults
          if (message.videoResults) {
            console.log('消息中的videoResults类型:', typeof message.videoResults);
            console.log('消息中的videoResults结构:', message.videoResults);
            
            // 如果是数组，直接使用
            if (Array.isArray(message.videoResults)) {
              safeVideoResults = message.videoResults;
            }
            // 如果是对象且有results字段，使用results字段
            else if (typeof message.videoResults === 'object' && Array.isArray(message.videoResults.results)) {
              safeVideoResults = message.videoResults.results;
            }
          }
          
          // 增强文本内容处理
          const messageText = message.text || message.content || '';
          
          // 渲染流式状态进度
          const renderStreamingStatus = (streamingStatus) => {
            if (!streamingStatus) return null;

            const { phase, message: statusMsg, plan, reasoning, steps, totalSteps, currentStep } = streamingStatus;

            return (
              <div className="streaming-status">
                {/* Planning 阶段 */}
                {phase === 'planning' && (
                  <div className="status-phase planning">
                    <div className="phase-indicator">
                      <span className="spinner">⚙️</span>
                      <span className="phase-label">规划阶段</span>
                    </div>
                    <p className="status-message">{statusMsg}</p>
                  </div>
                )}

                {/* Planning 完成 */}
                {phase === 'planning_complete' && (
                  <div className="status-phase planning-complete">
                    <div className="phase-indicator">
                      <span className="check-icon">✓</span>
                      <span className="phase-label">计划完成</span>
                    </div>
                    {plan && plan.length > 0 && (
                      <div className="plan-details">
                        <p className="plan-title">执行计划:</p>
                        <ol className="plan-steps">
                          {plan.map((step, idx) => (
                            <li key={idx}>{step}</li>
                          ))}
                        </ol>
                        {reasoning && <p className="reasoning"><strong>推理:</strong> {reasoning}</p>}
                      </div>
                    )}
                  </div>
                )}

                {/* Execution 阶段 */}
                {phase === 'execution' && (
                  <div className="status-phase execution">
                    <div className="phase-indicator">
                      <span className="spinner">⚡</span>
                      <span className="phase-label">执行阶段</span>
                    </div>
                    <p className="status-message">
                      正在执行步骤 {currentStep}/{totalSteps}
                    </p>
                    {steps && steps.length > 0 && (
                      <div className="execution-steps">
                        {steps.map((step) => (
                          <div key={step.number} className={`step step-${step.status}`}>
                            <div className="step-header">
                              <span className="step-number">步骤 {step.number}</span>
                              <span className="step-status">
                                {step.status === 'running' ? '🔄 执行中' : '✓ 完成'}
                              </span>
                            </div>
                            <p className="step-description">{step.description}</p>
                            {step.status === 'completed' && step.result && (
                              <p className="step-result">结果: {step.result.substring(0, 100)}...</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* 完成 */}
                {phase === 'complete' && (
                  <div className="status-phase complete">
                    <div className="phase-indicator">
                      <span className="check-icon">✓</span>
                      <span className="phase-label">完成</span>
                    </div>
                  </div>
                )}

                {/* 错误 */}
                {phase === 'error' && (
                  <div className="status-phase error">
                    <div className="phase-indicator">
                      <span className="error-icon">✗</span>
                      <span className="phase-label">错误</span>
                    </div>
                    <p className="error-message">{statusMsg}</p>
                  </div>
                )}
              </div>
            );
          };

          return (
            <div
                key={message.id}
                className={`message ${message.sender}`}
                data-has-videos={safeVideoResults.length > 0 ? 'true' : 'false'}
              >
                <div className="message-header">
                  <span className="message-sender">
                    {message.sender === 'ai' ? 'AI助手' : '您'}
                  </span>
                  <span className="message-time">{message.timestamp}</span>
                </div>

                {/* 显示流式状态 */}
                {message.streamingStatus && renderStreamingStatus(message.streamingStatus)}

                <div className="message-content">
                  <div
                    className="message-text"
                    ref={isLastMessage ? lastMessageRef : null}
                    dangerouslySetInnerHTML={{ __html: formatMessage(messageText, safeVideoResults) }}
                  ></div>
                </div>
              </div>
          );
        })}

        {isLoading && (
          <div className="loading-indicator">
            <div className="loading-spinner"></div>
            <span>正在生成回复...</span>
          </div>
        )}
      </div>

      {/* 输入框区域 */}
      <div className="chat-input-area">
        <div className="input-container">
          <textarea
            className="chat-input"
            value={inputValue}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题..."
            rows="1"
            disabled={isLoading}
          />
          <button 
            className="send-button"
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
          >
            {isLoading ? '发送中...' : '发送'}
          </button>
        </div>
      </div>

    </div>
  )
}

export default ChatInterface