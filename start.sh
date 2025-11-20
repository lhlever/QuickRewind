#!/bin/bash

# QuickRewind 一键启动脚本
# 同时启动前端和后端服务

echo "🚀 启动 QuickRewind 项目..."

# 检查是否在项目根目录
if [ ! -d "frontend" ] || [ ! -d "backend" ]; then
    echo "❌ 错误：请在项目根目录下运行此脚本"
    exit 1
fi

# 函数：检查端口是否被占用
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  警告：端口 $port 已被占用，$service 服务可能无法正常启动"
        return 1
    fi
    return 0
}

# 检查端口占用情况
check_port 8000 "后端"
check_port 5173 "前端"

# 函数：启动后端服务
start_backend() {
    echo "🔧 启动后端服务..."
    cd backend
    
    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        echo "❌ 错误：Python3 未安装"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo "📦 创建虚拟环境..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            echo "❌ 错误：创建虚拟环境失败"
            exit 1
        fi
    fi
    
    # 激活虚拟环境
    echo "🔧 激活虚拟环境..."
    source venv/bin/activate
    
    # 安装依赖
    echo "📦 安装后端依赖..."
    pip install -r requirements.txt
    
    # 启动后端服务
    echo "🚀 启动 FastAPI 服务 (端口: 8000)..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-buffer &
    BACKEND_PID=$!
    echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
    
    cd ..
    return $BACKEND_PID
}

# 函数：启动前端服务
start_frontend() {
    echo "🎨 启动前端服务..."
    cd frontend
    
    # 检查Node.js环境
    if ! command -v npm &> /dev/null; then
        echo "❌ 错误：Node.js/npm 未安装"
        exit 1
    fi
    
    # 安装依赖
    echo "📦 安装前端依赖..."
    npm install
    
    # 启动前端服务
    echo "🚀 启动 Vite 开发服务器 (端口: 5173)..."
    npm run dev &
    FRONTEND_PID=$!
    echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
    
    cd ..
    return $FRONTEND_PID
}

# 清理函数
cleanup() {
    echo "🧹 正在停止服务..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ 后端服务已停止"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✅ 前端服务已停止"
    fi
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 启动服务
start_backend
BACKEND_PID=$?

# 等待后端服务启动
sleep 3

start_frontend
FRONTEND_PID=$?

echo ""
echo "🎉 QuickRewind 项目已成功启动！"
echo ""
echo "📊 服务信息："
echo "   - 前端服务: http://localhost:5173"
echo "   - 后端服务: http://localhost:8000"
echo "   - API文档: http://localhost:8000/docs"
echo ""
echo "💡 提示："
echo "   - 按 Ctrl+C 停止所有服务"
echo "   - 后端PID: $BACKEND_PID"
echo "   - 前端PID: $FRONTEND_PID"
echo ""

# 等待用户中断
wait