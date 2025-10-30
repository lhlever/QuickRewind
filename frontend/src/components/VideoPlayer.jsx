import { useRef, useEffect, useState, forwardRef } from 'react'
import './VideoPlayer.css'

const VideoPlayer = forwardRef(({ video, videoData, initialTime = 0, autoPlay = false }, ref) => {
  const videoRef = useRef(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [volume, setVolume] = useState(80)

  // 转发ref到video元素
  useEffect(() => {
    if (ref) {
      if (typeof ref === 'function') {
        ref(videoRef.current)
      } else {
        ref.current = videoRef.current
      }
    }
  }, [ref])

  // 处理视频加载
  useEffect(() => {
    // 优先使用videoData
    const videoSource = videoData?.file || video;
    
    if (videoSource && videoRef.current) {
      try {
        if (videoSource.url) {
          videoRef.current.src = videoSource.url
        } else if (videoSource instanceof File) {
          // 为了演示，我们使用Blob URL
          const videoUrl = URL.createObjectURL(videoSource)
          videoRef.current.src = videoUrl
          
          // 清理函数
          return () => {
            URL.revokeObjectURL(videoUrl)
          }
        }
      } catch (error) {
        console.error('Video loading error:', error)
      }
    }
  }, [video, videoData])

  // 处理初始时间设置和自动播放
  useEffect(() => {
    if (videoRef.current) {
      if (initialTime !== null && 
          typeof initialTime === 'number' && isFinite(initialTime) && initialTime >= 0) {
        try {
          videoRef.current.currentTime = initialTime
        } catch (error) {
          console.warn('Failed to set currentTime:', error)
        }
      }
      
      if (autoPlay) {
        videoRef.current.play().catch(err => {
          console.warn('Auto play prevented:', err)
        })
        setIsPlaying(true)
      }
    }
  }, [initialTime, autoPlay])

  // 处理播放/暂停
  const togglePlayPause = () => {
    if (videoRef.current) {
      try {
        if (isPlaying) {
          videoRef.current.pause()
        } else {
          videoRef.current.play()
        }
        setIsPlaying(!isPlaying)
      } catch (error) {
        console.error('Play/pause error:', error)
      }
    }
  }

  // 处理静音切换
  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  // 处理音量变化
  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value)
    setVolume(newVolume)
    if (videoRef.current) {
      videoRef.current.volume = newVolume / 100
      videoRef.current.muted = newVolume === 0
      setIsMuted(newVolume === 0)
    }
  }

  // 格式化时间
  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="video-player-container">
      {videoData?.title && (
        <h2 className="video-title">{videoData.title}</h2>
      )}
      {/* 移除重复的标题栏，只保留主应用的标题栏 */}
      
      <div className="video-wrapper">
        <video
        id="main-video"
        ref={videoRef}
        className="video-element"
        onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
        onLoadedMetadata={(e) => setDuration(e.target.duration)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onClick={togglePlayPause}
      >
        您的浏览器不支持HTML5视频播放。
      </video>
        
        <div className="video-controls">
          <button 
            className="play-pause-btn"
            onClick={togglePlayPause}
            title={isPlaying ? '暂停' : '播放'}
          >
            {isPlaying ? '⏸️' : '▶️'}
          </button>
          
          <div className="time-display">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
          
          <input
            type="range"
            className="progress-bar"
            min="0"
            max={duration}
            value={currentTime}
            onChange={(e) => {
              const newTime = parseFloat(e.target.value)
              setCurrentTime(newTime)
              videoRef.current.currentTime = newTime
            }}
          />
          
          <button 
            className="volume-btn"
            onClick={toggleMute}
            title={isMuted ? '取消静音' : '静音'}
          >
            {isMuted ? '🔇' : '🔊'}
          </button>
          
          <input
            type="range"
            className="volume-slider"
            min="0"
            max="100"
            value={volume}
            onChange={handleVolumeChange}
            title="音量"
          />
        </div>
      </div>
    </div>
  )
})

VideoPlayer.displayName = 'VideoPlayer'

export default VideoPlayer