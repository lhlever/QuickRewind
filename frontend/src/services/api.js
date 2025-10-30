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
    // 搜索视频 - 返回完整的响应对象，包含message和videos字段
    search: async (query) => {
      try {
        const response = await request('/v1/videos/search', {
          method: 'POST',
          body: JSON.stringify({ query }),
        });
        
        console.log('API响应原始数据:', response);
        
        // 处理后端返回的完整格式: {message: string, is_matched: boolean, videos: []}
        if (response && typeof response === 'object') {
          // 确保videos数组存在且格式正确
          if (!response.videos || !Array.isArray(response.videos)) {
            response.videos = [];
          } else {
            // 处理每个视频对象，确保包含必要的字段
            response.videos = response.videos.map(item => ({
              id: item.id || (item.link ? item.link.split('/').pop() : String(Math.random())),
              title: item.title || '未命名视频',
              relevance: item.relevance !== undefined ? item.relevance : (item.similarity || 75),
              similarity: item.similarity !== undefined ? item.similarity : (item.relevance || 75),
              matchedSubtitles: item.matchedSubtitles || item.matched_subtitles || '',
              link: item.link || '',
              timestamp: item.timestamp || '',
              duration: item.duration || ''
            }));
          }
          
          // 如果没有message字段，生成一个默认消息
          if (!response.message) {
            response.message = `在视频库中找到 ${response.videos.length} 条与"${query}"相关的结果`;
          }
          
          // 返回完整的响应对象
          return response;
        }
        
        // 处理其他可能的响应格式
        if (Array.isArray(response)) {
          // 如果直接返回数组，包装成标准格式
          return {
            message: `在视频库中找到 ${response.length} 条与"${query}"相关的结果`,
            is_matched: response.length > 0,
            videos: response.map(item => ({
              id: item.id || String(Math.random()),
              title: item.title || '未命名视频',
              relevance: item.relevance || item.similarity || 75,
              similarity: item.similarity || item.relevance || 75,
              matchedSubtitles: item.matchedSubtitles || item.snippet || '',
              link: item.link || '',
              timestamp: item.timestamp || '',
              duration: item.duration || ''
            }))
          };
        } else if (response && Array.isArray(response.results)) {
          // 处理包含results数组的响应格式
          return {
            message: `在视频库中找到 ${response.results.length} 条与"${query}"相关的结果`,
            is_matched: response.results.length > 0,
            videos: response.results.map(item => ({
              id: item.id || String(Math.random()),
              title: item.title || '未命名视频',
              relevance: item.relevance || item.similarity || 75,
              similarity: item.similarity || item.relevance || 75,
              matchedSubtitles: item.matchedSubtitles || item.snippet || '',
              link: item.link || '',
              timestamp: item.timestamp || '',
              duration: item.duration || ''
            }))
          };
        }
        
        // 默认返回格式
        return {
          message: '未找到匹配的视频结果',
          is_matched: false,
          videos: []
        };
      } catch (error) {
        console.error('搜索视频失败:', error);
        // 返回错误状态的标准格式
        return {
          message: '搜索失败，请稍后重试',
          is_matched: false,
          videos: [],
          error: error.message
        };
      }
    },
    
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