// API服务配置和请求处理

// API基础URL - 修改为指向正确的后端地址
const API_BASE_URL = 'http://localhost:8000'; // 假设后端服务运行在8000端口

// 通用请求函数
const request = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      // 尝试获取响应中的错误信息
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorResponse = await response.json();
        if (errorResponse.detail) {
          errorMessage = errorResponse.detail;
        }
      } catch (e) {
        // 如果响应不是JSON格式，使用默认错误信息
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
};

// API服务对象
export const apiService = {
  // 视频相关API
  video: {
    // 搜索视频
    search: (query) => request('/v1/videos/search', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),
    
    // 上传视频
    upload: (formData, onProgress) => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable && onProgress) {
            const percentCompleted = Math.round((event.loaded * 100) / event.total);
            onProgress(percentCompleted);
          }
        });
        
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            // 尝试获取响应中的错误信息
            let errorMessage = `Upload failed with status ${xhr.status}`;
            try {
              const errorResponse = JSON.parse(xhr.responseText);
              if (errorResponse.detail) {
                errorMessage = errorResponse.detail;
              }
            } catch (e) {
              // 如果响应不是JSON格式，使用默认错误信息
            }
            reject(new Error(errorMessage));
          }
        });
        
        xhr.addEventListener('error', () => {
          reject(new Error('Network error during upload'));
        });
        
        xhr.open('POST', `${API_BASE_URL}/v1/videos/upload`);
        xhr.send(formData);
      });
    },
    
    // 获取视频详情
    getDetails: (videoId) => request(`/v1/videos/${videoId}`),
    
    // 获取视频大纲
    getOutline: (videoId) => request(`/v1/videos/${videoId}/outline`),
    
    // 获取视频处理状态
    getStatus: (videoId) => request(`/v1/videos/${videoId}/status`),
  },
  
  // Agent相关API
  agent: {
    // 发送消息给Agent
    sendMessage: (message) => request('/v1/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
    
    // 基于视频内容提问
    askAboutVideo: (videoId, question) => request('/v1/agent/video-query', {
      method: 'POST',
      body: JSON.stringify({ video_id: videoId, question }),
    }),
  },
};

export default apiService;