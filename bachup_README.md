# 秒回 QuickRewind

## 项目简介
快速回顾视频片段，解决视频信息密度低导致检索困难的问题

## 技术栈
| 层级  | 选型                       | 作用               | 替代方案                     |
| --- | ------------------------ | ---------------- | ------------------------ |
| 大模型 | Qwen2-7B-Instruct 🌟     | 语义改写/重排/总结       | GPT-4o、Claude-3、GLM-4    |
| 嵌入  | bert-base-chinese + CLIP | 文本&关键帧向量化        | m3e、bge-large、ViT-B-32   |
| 向量库 | Milvus 2.4 GPU 🌟        | 亿级片段秒级召回         | Weaviate、Qdrant、PGVector |
| 语音  | WhisperX                 | 时间戳级字幕           | FunASR、阿里云 ASR           |
| 框架  | LangChain 0.2 🌟         | ReAct Agent、链式编排 | LlamaIndex、Autogen       |
| 后端  | FastAPI + Python 3.11    | 3 个接口 + SSE 流式   | SpringBoot、Go-Gin        |
| 前端  | React + Antd + Vite      | 搜索框/播放器/反馈       | Vue、Svelte               |
| 存储  | MinIO (S3 协议)            | 片段缩略图&子视频        | 阿里云 OSS、AWS S3           |
| 部署  | Docker-Compose + Nginx   | 一键拉起 6 个服务       | K8s、Rainbond             |
| 监控  | LangSmith + Prometheus   | 调用链、token 成本     | Weights\&Biases          |


## 快速开始

### 环境要求
- Python 3.9+
- Docker (可选)

### 启动步骤
1. 安装依赖: `npm install` 或 `pip install -r requirements.txt`
2. 配置环境: 复制`.env.example`为`.env`并填写API密钥
3. 启动服务: `npm start` 或 `python main.py`
4. 访问地址: http://localhost:3000

### 评测运行
bash evaluate.sh

## 技术架构
(贴上架构图或文字描述)

## 核心功能
- [x] 功能1: 大模型调用
- [x] 功能2: RAG检索
- [x] 功能3: 评测系统
- [ ] 功能4: (未完成的)

## 性能指标
| 指标 | 数值 |
|------|------|
| 准确率 | 78% |
| 平均延迟 | 1.2s |
| Token消耗 | 450/次 |

## 团队分工(如果是小组)
- 张三: 前端开发、UI设计
- 李四: 后端架构、RAG实现
- 王五: 评测体系、文档编写