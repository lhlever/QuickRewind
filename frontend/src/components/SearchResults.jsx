import { useState } from 'react'
import './SearchResults.css'

const SearchResults = ({ results, onResultSelect, onViewOutline }) => {
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
        duration: convertDurationToSeconds(result.duration || '00:00:00')
      })
    }
  }

  // 处理查看大纲按钮点击
  const handleViewOutline = (result, event) => {
    event.stopPropagation() // 防止触发整个卡片的点击事件
    if (onViewOutline) {
      const mockOutline = generateMockOutline(result)
      onViewOutline({
        ...result,
        outline: mockOutline,
        duration: convertDurationToSeconds(result.duration || '00:00:00'),
        // 记录当前片段的时间范围以便高亮
        highlightSegment: {
          startTime: 0,
          endTime: 60 // 假设片段长度为60秒
        }
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
    const parts = duration?.split(':').map(Number) || [0, 0]
    if (parts.length === 2) {
      return parts[0] * 60 + parts[1]
    } else if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2]
    }
    return 0
  }

  return (
    <div className="search-results">
      {/* 卡片网格布局 */}
      <div className="results-grid">
        {results.map((result) => (
          <div 
            key={result.id}
            className={`video-card ${selectedResult === result.id ? 'selected' : ''}`}
            onClick={() => handleResultClick(result)}
          >
            {/* 视频缩略图区域 */}
            <div className="card-thumbnail">
              {/* 使用占位图替代真实缩略图 */}
              <div className="placeholder-thumbnail">
                <span className="video-icon">📹</span>
              </div>
              {result.relevance !== undefined && (
                <div className="similarity-badge">
                  {result.relevance}%
                </div>
              )}
            </div>
            
            {/* 卡片内容 */}
            <div className="card-content">
              {/* 视频标题 - 作为可点击链接 */}
              <h4 
                className="video-title clickable-title"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (onViewOutline) {
                    const mockOutline = generateMockOutline(result);
                    onViewOutline({
                      ...result,
                      outline: mockOutline,
                      duration: convertDurationToSeconds(result.duration || '00:00:00'),
                    });
                  }
                }}
              >
                {result.title}
              </h4>
              
              {/* 相似度信息 */}
              <div className="card-meta">
                <span className="similarity-label">相似度:</span>
                <span className="similarity-value">{result.relevance || 0}%</span>
              </div>
              
              {/* 匹配到的字幕 */}
              {result.matchedSubtitles && (
                <div className="matched-subtitles">
                  <div className="subtitle-label">匹配字幕:</div>
                  <div className="subtitle-text">{result.matchedSubtitles}</div>
                </div>
              )}
              
              {/* 操作按钮 */}
              <div className="card-actions">
                <button 
                  className="outline-btn"
                  onClick={(e) => handleViewOutline(result, e)}
                >
                  查看大纲
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* 无结果状态 */}
      {results.length === 0 && (
        <div className="no-results">
          <div className="no-results-icon">🔍</div>
          <p>未找到匹配的视频内容</p>
          <p className="suggestion">请尝试使用不同的关键词搜索</p>
        </div>
      )}
    </div>
  )
}

export default SearchResults