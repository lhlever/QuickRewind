import { useRef, useEffect, useState, forwardRef } from 'react'
import './VideoPlayer.css'

// 静态导入hls.js库
import Hls from 'hls.js';

// 确保Hls存在，在不支持的环境中提供后备
const SafeHls = typeof window !== 'undefined' ? Hls : null;

// 验证Hls库是否正确加载
if (SafeHls === null) {
  console.warn('Hls.js库未加载，可能是在非浏览器环境中');
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
        
        console.log('VideoPlayer: 开始检测视频URL来源');
        console.log('VideoPlayer: 传入的videoData:', videoData ? JSON.stringify(Object.keys(videoData)) : 'null');
        console.log('VideoPlayer: 传入的video参数:', video);
        
        // 1. 最高优先级：使用videoData.file.url（从App.jsx中的mergedVideoData.file.url传递）
        if (videoData?.file?.url) {
          finalVideoUrl = videoData.file.url;
          isHlsUrl = finalVideoUrl.endsWith('.m3u8') || finalVideoUrl.includes('/playlist.m3u8');
          console.log('VideoPlayer: [优先] 使用videoData.file.url:', finalVideoUrl, 'isHls:', isHlsUrl);
        }
        // 2. 其次检查是否有HLS播放列表
        else if (videoData?.hls_playlist) {
          finalVideoUrl = videoData.hls_playlist;
          isHlsUrl = true;
          console.log('VideoPlayer: 使用HLS播放列表:', finalVideoUrl);
        }
        // 3. 检查videoData中的filePath字段
        else if (videoData?.filePath) {
          finalVideoUrl = videoData.filePath;
          isHlsUrl = finalVideoUrl.endsWith('.m3u8');
          console.log('VideoPlayer: 使用videoData.filePath:', finalVideoUrl, 'isHls:', isHlsUrl);
        }
        // 4. 检查video是否为字符串
        else if (typeof video === 'string') {
          finalVideoUrl = video;
          isHlsUrl = finalVideoUrl.endsWith('.m3u8');
          console.log('VideoPlayer: 使用video字符串参数:', finalVideoUrl, 'isHls:', isHlsUrl);
        }
        // 5. 检查video对象是否有url属性
        else if (video && typeof video === 'object' && video.url) {
          finalVideoUrl = video.url;
          isHlsUrl = finalVideoUrl.endsWith('.m3u8');
          console.log('VideoPlayer: 使用video对象的url属性:', finalVideoUrl, 'isHls:', isHlsUrl);
        }
        else {
          console.error('VideoPlayer: 错误 - 未提供有效的视频URL', {
            videoDataKeys: videoData ? Object.keys(videoData) : 'null',
            hasFile: !!videoData?.file,
            hasFileUrl: !!videoData?.file?.url,
            hasHlsPlaylist: !!videoData?.hls_playlist,
            hasFilePath: !!videoData?.filePath,
            videoType: typeof video,
            videoKeys: video && typeof video === 'object' ? Object.keys(video) : 'n/a'
          });
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
          console.log('isHlsUrl: ', isHlsUrl);
          console.log('SafeHls: ', SafeHls);
          console.log('SafeHls.isSupported(): ', SafeHls?.isSupported());

          // 处理HLS视频
          if (isHlsUrl && SafeHls && SafeHls.isSupported()) {
            console.log('VideoPlayer: 使用HLS.js播放HLS视频');
            setIsHlsPlayback(true);
            
            try {
              // 创建HLS实例，添加调试选项
              const hls = new SafeHls({
                maxBufferLength: 30,
                maxMaxBufferLength: 60,
                startLevel: -1,
                maxBufferSize: 60 * 1024 * 1024,
                highBufferWatchdogPeriod: 3,
                lowBufferWatchdogPeriod: 0.5,
                enableWorker: true,  // 启用Web Worker处理
                debug: true  // 启用调试日志
              });
              
              // 将HLS实例附加到video元素
              hls.attachMedia(videoRef.current);
              
              // 加载HLS清单
              console.log('VideoPlayer: 开始加载HLS清单:', finalVideoUrl);
              hls.loadSource(finalVideoUrl);
              
              // HLS事件监听 - 详细记录每个阶段
              hls.on(SafeHls.Events.MANIFEST_PARSED, (event, data) => {
                console.log('VideoPlayer: HLS清单解析完成');
                console.log('VideoPlayer: 可用质量等级:', data.levels.length);
                setIsHlsPlayback(true);
                if (autoPlay) {
                  videoRef.current.play().catch(err => console.error('HLS自动播放失败:', err));
                }
              });
              
              hls.on(SafeHls.Events.FRAG_LOADED, () => {
                console.log('VideoPlayer: HLS片段加载成功');
              });
              
              hls.on(SafeHls.Events.FRAG_LOADING, () => {
                console.log('VideoPlayer: HLS片段加载中...');
              });
              
              hls.on(SafeHls.Events.ERROR, (event, data) => {
                console.error('VideoPlayer: HLS错误详情:', {
                  type: data.type,
                  details: data.details,
                  fatal: data.fatal,
                  url: data.url,
                  loader: data.loader
                });
                
                // 尝试恢复错误
                if (data.fatal) {
                  switch (data.type) {
                    case SafeHls.ErrorTypes.NETWORK_ERROR:
                      console.log('VideoPlayer: 网络错误，1秒后尝试恢复');
                      setTimeout(() => hls.startLoad(), 1000); // 添加延迟重试
                      break;
                    case SafeHls.ErrorTypes.MEDIA_ERROR:
                      console.log('VideoPlayer: 媒体错误，尝试恢复');
                      hls.recoverMediaError();
                      break;
                    case SafeHls.ErrorTypes.MANIFEST_ERROR:
                      console.log('VideoPlayer: 清单错误，1秒后重新加载');
                      setTimeout(() => hls.loadSource(finalVideoUrl), 1000);
                      break;
                    default:
                      console.log('VideoPlayer: 致命错误，无法恢复');
                      hls.destroy();
                      setIsHlsPlayback(false);
                      // 尝试使用原生HTML5播放作为后备
                      console.log('VideoPlayer: 尝试使用原生HTML5播放作为后备');
                      videoRef.current.src = finalVideoUrl;
                      videoRef.current.load();
                      break;
                  }
                } else {
                  // 非致命错误，只记录警告
                  console.warn('VideoPlayer: HLS非致命错误:', data.details);
                }
              });
              
              // 存储HLS实例引用
              hlsInstanceRef.current = hls;
            } catch (error) {
              console.error('VideoPlayer: 创建HLS实例失败:', error);
              setIsHlsPlayback(false);
              // 尝试使用原生HTML5播放作为后备
              console.log('VideoPlayer: 尝试使用原生HTML5播放作为后备');
              videoRef.current.src = finalVideoUrl;
              videoRef.current.load();
            }
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
  
  // 移除冗余的useEffect，因为videoData和video的变化已经在主要的useEffect中处理

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
      {/* {videoData?.title && (
        <h2 className="video-title">{videoData.title}</h2>
      )} */}
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