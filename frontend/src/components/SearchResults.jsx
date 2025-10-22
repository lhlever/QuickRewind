import { useState } from 'react'
import './SearchResults.css'

const SearchResults = ({ results, onResultSelect }) => {
  const [selectedResult, setSelectedResult] = useState(null)

  // 处理结果项点击
  const handleResultClick = (result) => {
    setSelectedResult(result.id)
    // 触发父组件的回调函数，以便在主界面中显示和播放视频
    if (onResultSelect) {
      // 生成模拟的视频大纲数据
      const mockOutline = generateMockOutline(result)
      
      onResultSelect({
        ...result,
        outline: mockOutline,
        // 为了演示，我们使用一个模拟文件对象
        file: {
          name: result.title,
          type: 'video/mp4',
          // 在实际应用中，这里应该是真实的视频文件URL或Blob
        },
        duration: convertDurationToSeconds(result.duration)
      })
    }
  }

  // 生成模拟的视频大纲数据
  const generateMockOutline = (result) => {
    // 根据搜索结果生成相关的大纲
    const sections = [
      {
        id: '1',
        title: `视频介绍 - ${result.title}`,
        startTime: 0,
        endTime: 60,
        subsections: [
          {
            id: '1.1',
            title: '主题概述',
            startTime: 0,
            endTime: 30
          },
          {
            id: '1.2',
            title: '背景信息',
            startTime: 30,
            endTime: 60
          }
        ]
      },
      {
        id: '2',
        title: '主要内容展示',
        startTime: 60,
        endTime: 180,
        subsections: [
          {
            id: '2.1',
            title: '核心要点',
            startTime: 60,
            endTime: 120
          },
          {
            id: '2.2',
            title: '实际应用',
            startTime: 120,
            endTime: 180
          }
        ]
      },
      {
        id: '3',
        title: '总结与结论',
        startTime: 180,
        endTime: 240,
        subsections: [
          {
            id: '3.1',
            title: '关键点回顾',
            startTime: 180,
            endTime: 210
          },
          {
            id: '3.2',
            title: '未来展望',
            startTime: 210,
            endTime: 240
          }
        ]
      }
    ]
    return sections
  }

  // 将时间格式转换为秒数
  const convertDurationToSeconds = (duration) => {
    // 假设duration格式为"MM:SS"或"HH:MM:SS"
    const parts = duration.split(':').map(Number)
    if (parts.length === 2) {
      return parts[0] * 60 + parts[1]
    } else if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2]
    }
    return 0
  }

  return (
    <div className="search-results">
    {/* 移除重复的标题栏，只保留主应用的标题栏 */}
      
      <div className="results-list">
        {results.map((result) => (
          <div 
            key={result.id}
            className={`result-item ${selectedResult === result.id ? 'selected' : ''}`}
            onClick={() => handleResultClick(result)}
          >
            <div className="result-thumbnail">
              <img 
                src={result.thumbnail} 
                alt={result.title} 
                loading="lazy"
                className="thumbnail-image"
              />
              <div className="time-badge">{result.timestamp}</div>
              <div className="play-overlay">
                <div className="play-icon">▶️</div>
              </div>
            </div>
            
            <div className="result-content">
              <h4 className="result-title">{result.title}</h4>
              <div className="result-meta">
                <span className="video-duration">{result.duration}</span>
                {result.relevance && (
                  <span className="relevance-score">
                    相关度: {result.relevance}%
                  </span>
                )}
              </div>
              <p className="result-snippet">{result.snippet}</p>
              
              {result.keywords && result.keywords.length > 0 && (
                <div className="result-keywords">
                  {result.keywords.map((keyword, index) => (
                    <span key={index} className="keyword-tag">
                      {keyword}
                    </span>
                  ))}
                </div>
              )}
            </div>
            
            <button className="play-result-button">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="8 5 19 12 8 19 8 5"></polygon>
              </svg>
            </button>
          </div>
        ))}
      </div>
      
      {results.length === 0 && (
        <div className="no-results">
          <div className="no-results-icon">🔍</div>
          <p>未找到匹配的视频内容</p>
          <p className="suggestion">请尝试使用不同的关键词搜索</p>
          <div className="search-tips">
            <p>提示：</p>
            <ul>
              <li>检查关键词是否拼写正确</li>
              <li>尝试使用更具体的词汇</li>
              <li>使用相关术语或技术词汇</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default SearchResults