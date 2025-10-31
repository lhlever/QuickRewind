import { useRef, useEffect, useState, forwardRef } from 'react'
import './VideoPlayer.css'

const VideoPlayer = forwardRef(({ video, videoData, initialTime = 0, autoPlay = false }, ref) => {
  const videoRef = useRef(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [volume, setVolume] = useState(80)
  const [isPlayPending, setIsPlayPending] = useState(false)

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
        // 重置播放状态
        setIsPlaying(false)
        setIsPlayPending(false)
        
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
    if (videoRef.current && initialTime >= 0) {
      // 确保视频已经加载了元数据
      const handleLoadedMetadata = () => {
        try {
          videoRef.current.currentTime = initialTime;
          if (autoPlay) {
            setIsPlayPending(true)
            videoRef.current.play()
              .then(() => {
                setIsPlaying(true)
                setIsPlayPending(false)
              })
              .catch(err => {
                console.warn('自动播放失败:', err);
                setIsPlaying(false)
                setIsPlayPending(false)
              });
          }
        } catch (err) {
          console.error('设置初始时间或自动播放错误:', err)
          setIsPlaying(false)
          setIsPlayPending(false)
        }
      };
      
      // 如果视频已经加载了元数据，直接设置时间
      if (videoRef.current.readyState >= 1) {
        handleLoadedMetadata();
      } else {
        // 否则监听loadedmetadata事件
        videoRef.current.addEventListener('loadedmetadata', handleLoadedMetadata);
        return () => {
          if (videoRef.current) {
            videoRef.current.removeEventListener('loadedmetadata', handleLoadedMetadata);
          }
        };
      }
    }
  }, [initialTime, autoPlay]);
  
  // 当videoData更新时确保视频正确加载
  useEffect(() => {
    // 这个逻辑已经在上面的useEffect中处理了
    // 这里可以添加其他针对videoData变化的处理逻辑
  }, [videoData])

  // 处理播放/暂停
  const togglePlayPause = () => {
    if (videoRef.current && !isPlayPending) {
      try {
        // 先检查视频的实际播放状态
        const currentPlaying = !videoRef.current.paused;
        
        if (currentPlaying || isPlaying) {
          videoRef.current.pause()
          setIsPlaying(false)
        } else {
          setIsPlayPending(true)
          videoRef.current.play()
            .then(() => {
              setIsPlaying(true)
              setIsPlayPending(false)
            })
            .catch(error => {
              console.error('播放失败:', error)
              setIsPlaying(false)
              setIsPlayPending(false)
            })
        }
      } catch (error) {
        console.error('播放/暂停错误:', error)
        setIsPlaying(false)
        setIsPlayPending(false)
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