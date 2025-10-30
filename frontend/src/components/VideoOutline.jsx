import { useState } from 'react'
import './VideoOutline.css'

const VideoOutline = ({ outline, onItemClick, highlightSegment }) => {
  const [expandedItems, setExpandedItems] = useState(new Set())

  // 格式化时间
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // 切换展开/折叠状态
  const toggleExpand = (id) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedItems(newExpanded)
  }

  // 处理点击播放
  const handleItemClick = (item) => {
    onItemClick(item.startTime)
  }

  // 检查项是否应该被高亮
  const shouldHighlight = (item) => {
    if (!highlightSegment) return false;
    
    // 检查当前项是否与高亮片段重叠
    const itemStartTime = item.startTime || 0;
    const itemEndTime = item.endTime || itemStartTime + 60; // 假设默认片段长度为60秒
    const highlightStart = highlightSegment.startTime || 0;
    const highlightEnd = highlightSegment.endTime || highlightStart + 60;
    
    // 检查时间范围重叠
    return (itemStartTime <= highlightEnd && itemEndTime >= highlightStart);
  }

  // 渲染大纲项
  const renderOutlineItem = (item, index) => {
    const isExpanded = expandedItems.has(item.id)
    const hasChildren = item.children && item.children.length > 0
    const isHighlighted = shouldHighlight(item)
    
    return (
      <div 
        key={item.id} 
        className={`outline-item ${index % 2 === 0 ? 'even' : 'odd'} ${isHighlighted ? 'highlighted' : ''}`}
      >
        <div 
          className="outline-item-header"
          onClick={() => handleItemClick(item)}
        >
          {hasChildren && (
            <span 
              className={`expand-icon ${isExpanded ? 'expanded' : ''}`}
              onClick={(e) => {
                e.stopPropagation()
                toggleExpand(item.id)
              }}
            >
              ▶
            </span>
          )}
          
          <span className="time-marker">{formatTime(item.startTime)}</span>
          
          <div className="item-content">
            <h4>{item.title}</h4>
            {item.snippet && (
              <p className="snippet">{item.snippet}</p>
            )}
          </div>
          
          <button className="play-button">▶️</button>
        </div>
        
        {hasChildren && isExpanded && (
          <div className="outline-children">
            {item.children.map((child, childIndex) => 
              renderOutlineItem(child, childIndex)
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="video-outline">
      <div className="outline-header">
        <h3>视频大纲</h3>
        <p>点击章节快速跳转到相应时间点</p>
      </div>
      
      <div className="outline-content">
        {outline.length === 0 ? (
          <div className="empty-outline">
            <p>暂无视频大纲</p>
          </div>
        ) : (
          outline.map((item, index) => renderOutlineItem(item, index))
        )}
      </div>
    </div>
  )
}

export default VideoOutline