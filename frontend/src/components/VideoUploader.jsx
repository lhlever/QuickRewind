import { useState, useRef } from 'react'
import './VideoUploader.css'

const VideoUploader = ({ onUploadComplete }) => {
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  // 处理文件选择
  const handleFileSelect = (event) => {
    const file = event.target.files[0]
    // 支持的视频MIME类型
    const validTypes = [
      'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime', // MOV
      'video/x-msvideo', // AVI
      'video/x-matroska', // MKV
      'video/x-flv', // FLV
      'video/x-ms-wmv', // WMV
      'video/mpeg', // MPEG, MPG
      'video/3gpp', // 3GP
      'video/3gpp2' // 3G2
    ];
    
    if (file && validTypes.includes(file.type)) {
      handleFile(file)
    } else if (file) {
      // 显示更具体的错误信息
      const fileExt = file.name.split('.').pop().toLowerCase();
      alert(`文件类型不支持。请上传有效的视频文件。当前文件扩展名: ${fileExt}`);
    }
  }

  // 处理拖拽事件
  const handleDragOver = (event) => {
    event.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    
    const file = event.dataTransfer.files[0]
    if (file && file.type.startsWith('video/')) {
      handleFile(file)
    }
  }

  // 处理文件上传逻辑
  const handleFile = (file) => {
    setSelectedFile(file)
    
    // 模拟上传进度
    let progress = 0
    const interval = setInterval(() => {
      progress += 5
      setUploadProgress(progress)
      
      if (progress >= 100) {
        clearInterval(interval)
        // 上传完成后调用回调函数
        setTimeout(() => {
          onUploadComplete(file)
        }, 500)
      }
    }, 100)
  }

  // 触发文件选择对话框
  const triggerFileSelect = () => {
    fileInputRef.current.click()
  }

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="uploader-container">
      <div className="uploader-header">
        <h2>上传视频</h2>
        <p>上传视频后，系统将自动生成视频大纲和关键片段</p>
      </div>
      
      <div 
        className={`uploader-dropzone ${isDragging ? 'dragging' : ''}`}
        onClick={triggerFileSelect}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          ref={fileInputRef}
          accept="video/*"
          className="file-input"
          onChange={handleFileSelect}
        />
        
        {!selectedFile ? (
          <div className="dropzone-content">
            <div className="upload-icon">📁</div>
            <h3>点击或拖拽视频文件到此处</h3>
            <p>支持 MP4, WebM, MOV 等格式</p>
            <p className="file-size-limit">最大文件大小: 2GB</p>
          </div>
        ) : (
          <div className="upload-preview">
            <div className="file-info">
              <div className="file-icon">🎬</div>
              <div className="file-details">
                <h4>{selectedFile.name}</h4>
                <p>{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            
            <div className="progress-container">
              <div 
                className="progress-bar" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            
            <p className="progress-text">{uploadProgress}% 已上传</p>
          </div>
        )}
      </div>
      
      <div className="uploader-tips">
        <h4>提示:</h4>
        <ul>
          <li>高质量视频将获得更精确的内容分析</li>
          <li>视频时长建议在 5-60 分钟之间</li>
          <li>上传后的视频将被加密处理，仅您可访问</li>
        </ul>
      </div>
    </div>
  )
}

export default VideoUploader