// API服务配置和请求处理

// API基础URL - 修改为指向正确的后端地址
const API_BASE_URL = 'http://localhost:8000'; // 假设后端服务运行在8000端口

// 通用请求函数
const request = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // 获取认证令牌
  const token = localStorage.getItem('token');
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };
  
  // 如果有令牌，添加到请求头
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
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
    // 获取视频基本信息
    getVideoInfo: async (videoId) => {
      console.log(`正在获取视频信息: ${videoId}`);
      try {
        const response = await request(`/api/v1/videos/${videoId}`);
        console.log(`成功获取视频信息:`, response);
        return response;
      } catch (error) {
        console.error(`获取视频信息失败:`, error);
        throw error;
      }
    },
    // 获取视频大纲
    getOutline: async (videoId) => {
      console.log(`正在获取视频大纲: ${videoId}`);
      try {
        const response = await request(`/api/v1/videos/${videoId}/outline`);
        console.log(`成功获取视频大纲:`, response);
        return response;
      } catch (error) {
        console.error(`获取视频大纲失败:`, error);
        throw error;
      }
    },
    
    // 搜索视频 - 返回完整的响应对象，包含message和videos字段
    search: async (query) => {
      try {
        const response = await request('/api/v1/videos/search', {
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
        
        xhr.open('POST', `${API_BASE_URL}/api/v1/videos/upload`);
        
        // 添加认证token到请求头
        const token = localStorage.getItem('token');
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }
        
        xhr.send(formData);
      });
    },

    // 获取视频详情
    getDetails: (videoId) => request(`/api/v1/videos/${videoId}`),

    // 获取视频大纲
    getOutline: (videoId) => request(`/api/v1/videos/${videoId}/outline`),

    // 获取视频处理状态
    getStatus: (videoId) => request(`/api/v1/videos/${videoId}/status`),

    // 获取用户视频列表
    getUserVideos: (skip = 0, limit = 20) => {
      const token = localStorage.getItem('token');
      return request(`/api/v1/videos/user/videos?skip=${skip}&limit=${limit}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },
  },
  
  // Agent相关API
  agent: {
    // 发送消息给Agent - 改为调用 stream 端点
    sendMessage: async (message) => {
      console.log('[sendMessage-改造] 被调用，将使用 stream 端点');

      // 收集所有事件
      let finalResult = {
        success: true,
        response: '',
        video_info: [],
        processing_time: 0
      };

      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/api/v1/agent/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
          },
          body: JSON.stringify({ message })
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                console.log('[sendMessage-改造] 收到事件:', data.type);

                // 只关心最终的 complete 事件
                if (data.type === 'complete') {
                  finalResult.response = data.final_answer || '';
                  finalResult.video_info = data.video_info || [];
                  finalResult.processing_time = data.processing_time || 0;
                }
              } catch (e) {
                console.error('[sendMessage-改造] 解析失败:', e);
              }
            }
          }
        }

        console.log('[sendMessage-改造] 返回最终结果:', finalResult);
        return finalResult;
      } catch (error) {
        console.error('[sendMessage-改造] 失败:', error);
        throw error;
      }
    },

    // 发送消息给Agent - SSE流式返回 - 使用 XMLHttpRequest 避免缓冲
    sendMessageStream: async (message, callbacks = {}) => {
      return new Promise((resolve, reject) => {
        const startTime = Date.now();
        console.log('[sendMessageStream-XHR] ========== 开始SSE流式请求 ==========');
        console.log('[sendMessageStream-XHR] 消息内容:', message);
        console.log('[sendMessageStream-XHR] 回调函数:', Object.keys(callbacks));

        const {
          onPlanningStart,
          onPlanningComplete,
          onExecutionStart,
          onStepStart,
          onStepComplete,
          onComplete,
          onError
        } = callbacks;

        const token = localStorage.getItem('token');
        const url = `${API_BASE_URL}/api/v1/agent/chat/stream`;

        const xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Accept', 'text/event-stream');
        xhr.setRequestHeader('Cache-Control', 'no-cache');
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }

        let buffer = '';
        let eventCount = 0;
        let lastPosition = 0;

        // 监听进度事件 - 实时接收数据
        xhr.onprogress = (e) => {
          const progressTime = Date.now() - startTime;
          console.log(`[sendMessageStream-XHR] [${progressTime}ms] onprogress触发 (loaded: ${e.loaded} bytes, total: ${e.total})`);

          // 获取新数据
          const newData = xhr.responseText.substring(lastPosition);
          lastPosition = xhr.responseText.length;

          if (!newData) return;

          console.log(`[sendMessageStream-XHR] [${progressTime}ms] 收到新数据: ${newData.length} bytes`);

          // 将新数据添加到缓冲区
          buffer += newData;
          const lines = buffer.split('\n');

          // 保留最后一个可能不完整的行
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              eventCount++;
              try {
                const data = JSON.parse(line.slice(6));
                const eventTime = Date.now() - startTime;
                console.log(`[sendMessageStream-XHR] [${eventTime}ms] 事件 #${eventCount}: ${data.type}`);

                // 立即同步调用回调
                switch (data.type) {
                  case 'connected':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 连接成功`);
                    break;
                  case 'planning_start':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 触发 onPlanningStart`);
                    onPlanningStart && onPlanningStart(data);
                    break;
                  case 'planning_complete':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 触发 onPlanningComplete`);
                    onPlanningComplete && onPlanningComplete(data);
                    break;
                  case 'execution_start':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 触发 onExecutionStart`);
                    onExecutionStart && onExecutionStart(data);
                    break;
                  case 'step_start':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 触发 onStepStart`);
                    onStepStart && onStepStart(data);
                    break;
                  case 'step_complete':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 触发 onStepComplete`);
                    onStepComplete && onStepComplete(data);
                    break;
                  case 'complete':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 触发 onComplete`);
                    onComplete && onComplete(data);
                    break;
                  case 'error':
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 触发 onError`);
                    onError && onError(data);
                    break;
                  default:
                    console.log(`[sendMessageStream-XHR] [${eventTime}ms] 未知事件类型:`, data.type);
                }
              } catch (e) {
                console.error('[sendMessageStream-XHR] 解析SSE数据失败:', e, line);
              }
            } else if (line.startsWith(':')) {
              console.log(`[sendMessageStream-XHR] [${Date.now() - startTime}ms] 心跳`);
            }
          }
        };

        xhr.onload = () => {
          const totalTime = Date.now() - startTime;
          console.log(`[sendMessageStream-XHR] [${totalTime}ms] 请求完成，共收到 ${eventCount} 个事件`);
          console.log('[sendMessageStream-XHR] ========== SSE流式请求结束 ==========');
          resolve();
        };

        xhr.onerror = (e) => {
          const errorTime = Date.now() - startTime;
          console.error(`[sendMessageStream-XHR] [${errorTime}ms] 请求失败:`, e);
          const error = new Error('Network error');
          onError && onError({ error: error.message });
          reject(error);
        };

        xhr.onabort = () => {
          const abortTime = Date.now() - startTime;
          console.log(`[sendMessageStream-XHR] [${abortTime}ms] 请求被中止`);
          reject(new Error('Request aborted'));
        };

        // 发送请求
        console.log('[sendMessageStream-XHR] 发送请求:', JSON.stringify({ message }));
        xhr.send(JSON.stringify({ message }));
      });
    },

    // 基于视频内容提问
    askAboutVideo: (videoId, question) => request('/api/v1/agent/video-query', {
      method: 'POST',
      body: JSON.stringify({ video_id: videoId, question }),
    }),

    // 💡 WebSocket 实时流式通信（真正的实时，不受localhost缓冲影响）
    sendMessageWebSocket: (message, callbacks = {}) => {
      return new Promise((resolve, reject) => {
        const startTime = Date.now();
        console.log('[WebSocket] ========== 开始WebSocket连接 ==========');
        console.log('[WebSocket] 消息内容:', message);
        console.log('[WebSocket] 回调函数:', Object.keys(callbacks));

        const {
          onPlanningStart,
          onPlanningComplete,
          onExecutionStart,
          onStepStart,
          onStepComplete,
          onComplete,
          onError
        } = callbacks;

        const token = localStorage.getItem('token');
        const wsUrl = `ws://localhost:8000/api/v1/agent/ws/chat`;

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          const connectTime = Date.now() - startTime;
          console.log(`[WebSocket] [${connectTime}ms] WebSocket连接成功`);

          // 发送消息
          ws.send(JSON.stringify({
            message,
            ...(token && { token })
          }));
          console.log('[WebSocket] 已发送消息到服务器');
        };

        ws.onmessage = (event) => {
          const messageTime = Date.now() - startTime;

          try {
            const data = JSON.parse(event.data);
            console.log(`[WebSocket] [${messageTime}ms] 收到消息: ${data.type}`);

            // 立即调用对应的回调函数
            switch (data.type) {
              case 'connected':
                console.log(`[WebSocket] [${messageTime}ms] 连接确认`);
                break;

              case 'planning_start':
                console.log(`[WebSocket] [${messageTime}ms] 触发 onPlanningStart`);
                onPlanningStart && onPlanningStart(data);
                break;

              case 'planning_complete':
                console.log(`[WebSocket] [${messageTime}ms] 触发 onPlanningComplete`);
                onPlanningComplete && onPlanningComplete(data);
                break;

              case 'execution_start':
                console.log(`[WebSocket] [${messageTime}ms] 触发 onExecutionStart`);
                onExecutionStart && onExecutionStart(data);
                break;

              case 'step_start':
                console.log(`[WebSocket] [${messageTime}ms] 触发 onStepStart`);
                onStepStart && onStepStart(data);
                break;

              case 'step_complete':
                console.log(`[WebSocket] [${messageTime}ms] 触发 onStepComplete`);
                onStepComplete && onStepComplete(data);
                break;

              case 'complete':
                console.log(`[WebSocket] [${messageTime}ms] 触发 onComplete`);
                onComplete && onComplete(data);
                ws.close();
                resolve();
                break;

              case 'error':
                console.error(`[WebSocket] [${messageTime}ms] 触发 onError`);
                onError && onError(data);
                ws.close();
                reject(new Error(data.error));
                break;

              default:
                console.log(`[WebSocket] [${messageTime}ms] 未知事件类型:`, data.type);
            }
          } catch (e) {
            console.error('[WebSocket] 解析消息失败:', e, event.data);
          }
        };

        ws.onerror = (error) => {
          const errorTime = Date.now() - startTime;
          console.error(`[WebSocket] [${errorTime}ms] WebSocket错误:`, error);
          const err = new Error('WebSocket connection error');
          onError && onError({ error: err.message });
          reject(err);
        };

        ws.onclose = () => {
          const closeTime = Date.now() - startTime;
          console.log(`[WebSocket] [${closeTime}ms] WebSocket连接关闭`);
          console.log('[WebSocket] ========== WebSocket通信结束 ==========');
        };
      });
    },
  },
  
  // 用户管理相关API
  user: {
    // 获取用户列表
    getUsers: (params = '') => {
      // 从localStorage获取token
      const token = localStorage.getItem('token');
      return request(`/api/v1/users${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },

    // 获取用户详情
    getUser: (userId) => {
      const token = localStorage.getItem('token');
      return request(`/api/v1/users/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },

    // 创建用户
    createUser: (userData) => {
      const token = localStorage.getItem('token');
      return request('/api/v1/users/', {
        method: 'POST',
        body: JSON.stringify(userData),
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },

    // 更新用户
    updateUser: (userId, userData) => {
      const token = localStorage.getItem('token');
      return request(`/api/v1/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(userData),
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },

    // 删除用户
    deleteUser: (userId) => {
      const token = localStorage.getItem('token');
      return request(`/api/v1/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },

    // 切换用户状态
    toggleUserStatus: (userId, isActive) => {
      const token = localStorage.getItem('token');
      return request(`/api/v1/users/${userId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: isActive }),
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },

    // 切换用户角色
    toggleUserRole: (userId, isAdmin) => {
      const token = localStorage.getItem('token');
      return request(`/api/v1/users/${userId}/role`, {
        method: 'PUT',
        body: JSON.stringify({ is_superuser: isAdmin }),
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    }
  },
};

export default apiService;