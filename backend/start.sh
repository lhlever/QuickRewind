#!/bin/bash

# QuickRewind后端服务启动脚本

echo "Starting QuickRewind Backend Service..."

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "Error: Python3 is not installed."
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
fi

# 激活虚拟环境
echo "Activating virtual environment..."
source venv/bin/activate

# 升级pip
echo "Upgrading pip..."
pip install --upgrade pip

# 安装依赖
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi

# 检查.env文件是否存在
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using default settings."
    echo "Please create a .env file with the appropriate configuration."
fi

# 启动应用
echo "Starting FastAPI application..."
echo "Application will be available at http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"

# 使用uvicorn启动应用
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload