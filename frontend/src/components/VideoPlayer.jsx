import { useRef, useEffect, useState, forwardRef } from 'react'
import './VideoPlayer.css'

// 动态导入hls.js库
let Hls = null;
try {
  // 检查是否支持hls.js
  if (typeof window !== 'undefined') {
    // 动态导入避免SSR问题
    const hlsModule = require('hls.js');
    Hls = hlsModule.default || hlsModule;
  }
} catch (error) {
  console.warn('hls.js库加载失败:', error);
  Hls = null;
}

const VideoPlayer = forwardRef(({ video, videoData, initialTime = 0, autoPlay = false }, ref) => {
  const videoRef = useRef(null)
  const hlsInstanceRef = useRef(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [volume, setVolume] = useState(80)
  const [isPlayPending, setIsPlayPending] = useState(false)
  const [isHlsPlayback, setIsHlsPlayback] = useState(false)

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

  // 清理HLS实例
  const cleanupHlsInstance = () => {
    if (hlsInstanceRef.current) {
      console.log('VideoPlayer: 清理HLS实例');
      hlsInstanceRef.current.destroy();
      hlsInstanceRef.current = null;
      setIsHlsPlayback(false);
    }
  };

  // 处理视频加载
  useEffect(() => {
    console.log('VideoPlayer: 视频数据更新', { videoData, video });
    
    // 首先清理之前的HLS实例
    cleanupHlsInstance();
    
    if (videoRef.current) {
      try {
        // 重置播放状态
        setIsPlaying(false)
        setIsPlayPending(false)
        
        // 重置视频元素
        videoRef.current.src = '';
        
        // 确定要播放的视频URL
        let finalVideoUrl = null;
        let isHlsUrl = false;
        
        // 优先检查是否有HLS播放列表
        if (videoData && videoData.hls_playlist) {
          finalVideoUrl = videoData.hls_playlist;
          isHlsUrl = true;
          console.log('VideoPlayer: 使用HLS播放列表:', finalVideoUrl);
        }
        // 其次使用videoData中的filePath字段
        else if (videoData && videoData.filePath) {
          finalVideoUrl = videoData.filePath;
          isHlsUrl = finalVideoUrl.endsWith('.m3u8');
          console.log('VideoPlayer: 使用videoData中的filePath:', finalVideoUrl, 'isHls:', isHlsUrl);
        }
        // 其次尝试使用videoSource.url
        else if (videoData?.file && videoData.file.url) {
          finalVideoUrl = videoData.file.url;
          isHlsUrl = finalVideoUrl.endsWith('.m3u8');
          console.log('VideoPlayer: 使用videoData.file.url:', finalVideoUrl, 'isHls:', isHlsUrl);
        }
        // 最后尝试直接使用video参数
        else if (video) {
          finalVideoUrl = video;
          isHlsUrl = finalVideoUrl.endsWith('.m3u8');
          console.log('VideoPlayer: 使用video参数:', finalVideoUrl, 'isHls:', isHlsUrl);
        } else {
          console.error('VideoPlayer: 错误 - 未提供有效的视频URL');
          finalVideoUrl = null;
        }
        
        if (finalVideoUrl) {
          // 添加基础事件监听器
          const handleLoadedData = () => {
            console.log('VideoPlayer: 视频数据已加载');
          };
          
          const handleError = (e) => {
            console.error('VideoPlayer: 视频加载错误', e);
            if (videoRef.current) {
              console.log('VideoPlayer: 视频错误对象', videoRef.current.error);
              console.error('VideoPlayer: 错误 - 视频加载失败，无法播放。请检查视频URL是否正确:', finalVideoUrl);
            }
          };
          
          const handleCanPlay = () => {
            console.log('VideoPlayer: 视频可以播放了');
            if (autoPlay) {
              videoRef.current.play().catch(err => console.error('自动播放失败:', err));
            }
          };
          
          const handleLoadStart = () => {
            console.log('VideoPlayer: 开始加载视频');
          };
          
          videoRef.current.addEventListener('loadstart', handleLoadStart);
          videoRef.current.addEventListener('loadeddata', handleLoadedData);
          videoRef.current.addEventListener('canplay', handleCanPlay);
          videoRef.current.addEventListener('error', handleError);
          
          // 处理HLS视频
          if (isHlsUrl && Hls && Hls.isSupported()) {
            console.log('VideoPlayer: 使用HLS.js播放HLS视频');
            
            // 创建HLS实例
            const hls = new Hls({
              maxBufferLength: 30,  // 最大缓冲区长度（秒）
              maxMaxBufferLength: 60, // 最大最大缓冲区长度
              startLevel: -1,  // 自动选择最佳质量
              maxBufferSize: 60 * 1024 * 1024, // 最大缓冲区大小（字节）
              highBufferWatchdogPeriod: 3, // 高缓冲监控周期（秒）
              lowBufferWatchdogPeriod: 0.5 // 低缓冲监控周期（秒）
            });
            
            // 将HLS实例附加到video元素
            hls.attachMedia(videoRef.current);
            
            // 加载HLS清单
            hls.loadSource(finalVideoUrl);
            
            // HLS事件监听
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
              console.log('VideoPlayer: HLS清单解析完成');
              setIsHlsPlayback(true);
              if (autoPlay) {
                videoRef.current.play().catch(err => console.error('HLS自动播放失败:', err));
              }
            });
            
            hls.on(Hls.Events.ERROR, (event, data) => {
              console.error('VideoPlayer: HLS错误', data);
              
              // 尝试恢复错误
              if (data.fatal) {
                switch (data.type) {
                  case Hls.ErrorTypes.NETWORK_ERROR:
                    console.log('VideoPlayer: 网络错误，尝试恢复');
                    hls.startLoad();
                    break;
                  case Hls.ErrorTypes.MEDIA_ERROR:
                    console.log('VideoPlayer: 媒体错误，尝试恢复');
                    hls.recoverMediaError();
                    break;
                  default:
                    console.log('VideoPlayer: 致命错误，无法恢复');
                    hls.destroy();
                    setIsHlsPlayback(false);
                    break;
                }
              }
            });
            
            // 存储HLS实例引用
            hlsInstanceRef.current = hls;
          } else {
            // 处理非HLS视频
            console.log('VideoPlayer: 使用标准HTML5视频播放');
            videoRef.current.src = finalVideoUrl;
            videoRef.current.load();
          }
          
          // 清理函数
          return () => {
            // 清理HLS实例
            cleanupHlsInstance();
            
            // 移除事件监听器
            if (videoRef.current) {
              videoRef.current.removeEventListener('loadstart', handleLoadStart);
              videoRef.current.removeEventListener('loadeddata', handleLoadedData);
              videoRef.current.removeEventListener('canplay', handleCanPlay);
              videoRef.current.removeEventListener('error', handleError);
              console.log('VideoPlayer: 已移除所有事件监听器');
            }
          };
        } else {
          console.error('VideoPlayer: 未设置视频源，无法加载视频');
        }
      } catch (error) {
        console.error('VideoPlayer: 视频加载错误:', error);
        cleanupHlsInstance();
      }
    } else {
      console.warn('VideoPlayer: 没有视频元素');
    }
  }, [video, videoData, autoPlay])

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
              // 对于HLS视频，直接设置currentTime就可以工作，因为hls.js已经附加到video元素
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