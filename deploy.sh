#!/bin/bash

# 设置错误时退出
set -e

# 读取环境变量
source .env

# 检查必要的环境变量
if [ -z "$ECS_IP" ] || [ -z "$ECS_USERNAME" ] || [ -z "$ECS_PASSWORD" ]; then
    echo "错误: 请确保在.env文件中设置了ECS_IP、ECS_USERNAME和ECS_PASSWORD"
    exit 1
fi

# 检查并安装本地依赖
echo "检查并安装本地依赖..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "检测到 macOS 系统..."
    if ! command -v sshpass &> /dev/null; then
        echo "正在安装 sshpass..."
        if ! command -v brew &> /dev/null; then
            echo "正在安装 Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            if [[ $(uname -m) == "arm64" ]]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            else
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        fi
        brew install hudochenkov/sshpass/sshpass || {
            echo "错误: sshpass 安装失败"
            exit 1
        }
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v yum &> /dev/null; then
        # CentOS/RHEL
        if ! command -v sshpass &> /dev/null; then
            echo "正在安装 sshpass..."
            sudo yum install -y sshpass || {
                echo "错误: sshpass 安装失败"
                exit 1
            }
        fi
    elif command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        if ! command -v sshpass &> /dev/null; then
            sudo apt-get update
            echo "正在安装 sshpass..."
            sudo apt-get install -y sshpass || {
                echo "错误: sshpass 安装失败"
                exit 1
            }
        fi
    else
        echo "错误: 不支持的包管理器"
        exit 1
    fi
else
    echo "错误: 不支持的操作系统"
    exit 1
fi

# 验证所需工具是否已安装
echo "验证必要工具..."
for cmd in sshpass ssh; do
    if ! command -v $cmd &> /dev/null; then
        echo "错误: $cmd 未安装或不在 PATH 中"
        exit 1
    fi
done

# 测试连接
echo "测试SSH连接..."
if ! sshpass -p "$ECS_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $ECS_USERNAME@$ECS_IP "echo 'SSH连接成功'"; then
    echo "错误: 无法连接到服务器，请检查IP地址、用户名和密码是否正确"
    exit 1
fi

# 创建远程目录结构
echo "创建远程目录结构..."
sshpass -p "$ECS_PASSWORD" ssh -o StrictHostKeyChecking=no $ECS_USERNAME@$ECS_IP "mkdir -p ~/video-maker/{temp,output,logs}"

# 创建临时打包文件
echo "打包项目文件..."
tar --exclude='.git' \
    --exclude='temp' \
    --exclude='output' \
    --exclude='logs' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='deploy.tar.gz' \
    -czf deploy.tar.gz .

# 传输项目文件
echo "传输项目文件到服务器..."
sshpass -p "$ECS_PASSWORD" scp -o StrictHostKeyChecking=no deploy.tar.gz $ECS_USERNAME@$ECS_IP:~/video-maker/
sshpass -p "$ECS_PASSWORD" ssh -o StrictHostKeyChecking=no $ECS_USERNAME@$ECS_IP "cd ~/video-maker && tar xzf deploy.tar.gz && rm deploy.tar.gz"

# 删除本地临时文件
rm deploy.tar.gz

# 复制环境变量文件
echo "复制环境变量文件..."
sshpass -p "$ECS_PASSWORD" scp -o StrictHostKeyChecking=no .env $ECS_USERNAME@$ECS_IP:~/video-maker/

# 在远程服务器上设置Python环境并安装依赖
echo "设置Python环境..."
sshpass -p "$ECS_PASSWORD" ssh -o StrictHostKeyChecking=no $ECS_USERNAME@$ECS_IP "cd ~/video-maker && \
    sudo yum update -y && \
    sudo yum install -y python3-pip python3-devel gcc && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt"

# 设置服务自启动
echo "设置服务自启动..."
SERVICE_FILE="[Unit]
Description=Video Maker Service
After=network.target

[Service]
Type=simple
User=$ECS_USERNAME
WorkingDirectory=/root/video-maker
Environment=PATH=/root/video-maker/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/root/video-maker/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target"

echo "$SERVICE_FILE" | sshpass -p "$ECS_PASSWORD" ssh $ECS_USERNAME@$ECS_IP "sudo tee /etc/systemd/system/video-maker.service"

# 启动服务
echo "启动服务..."
sshpass -p "$ECS_PASSWORD" ssh $ECS_USERNAME@$ECS_IP "sudo systemctl daemon-reload && \
    sudo systemctl enable video-maker && \
    sudo systemctl start video-maker"

echo "部署完成！"
echo "可以使用以下命令查看服务状态："
echo "sshpass -p \$ECS_PASSWORD ssh \$ECS_USERNAME@\$ECS_IP 'sudo systemctl status video-maker'" 