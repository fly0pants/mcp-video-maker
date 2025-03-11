#!/bin/bash

# 视频生成系统真实API测试脚本

echo "======================================"
echo "      视频生成系统真实API测试工具      "
echo "======================================"
echo ""

# 确认当前目录是项目根目录
if [ ! -f "models/video.py" ]; then
    echo "错误: 请在项目根目录中运行此脚本"
    exit 1
fi

# 激活 Python 虚拟环境
echo "激活 Python 虚拟环境..."
if [ -d ".venv" ]; then
    # 使用项目内的虚拟环境
    source .venv/bin/activate
else
    echo "警告: 未找到项目虚拟环境 (.venv)"
    echo "请确保您已经激活了正确的 Python 环境"
fi

# 获取当前目录
PROJECT_DIR=$(pwd)
echo "项目目录: $PROJECT_DIR"

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ]; then
    echo "警告: 未设置 OPENAI_API_KEY 环境变量"
    echo "请设置您的 OpenAI API 密钥，例如: export OPENAI_API_KEY='your_api_key'"
    echo -n "请输入您的 OpenAI API 密钥 (或按 Enter 跳过): "
    read api_key
    if [ ! -z "$api_key" ]; then
        export OPENAI_API_KEY="$api_key"
        echo "已设置 OPENAI_API_KEY 环境变量"
    else
        echo "继续而不设置 API 密钥 (测试可能会失败)"
    fi
else
    echo "已检测到 OPENAI_API_KEY 环境变量"
fi

# 检查日志目录
if [ ! -d "logs" ]; then
    mkdir logs
    echo "创建日志目录: logs/"
fi

# 确认要运行的测试
echo ""
echo "可用的测试:"
echo "1) script - 脚本创建测试"
echo "2) storyboard_content - 分镜内容创建测试"
echo "3) storyboard_process - 分镜处理测试"
echo "4) storyboard_images - 分镜图像生成测试"
echo "5) workflow - 完整工作流测试"
echo "6) all - 运行所有测试"
echo ""
echo -n "请选择要运行的测试 (默认: script): "
read test_choice

test_args=""
case $test_choice in
    1|"script")
        test_args="--tests script"
        ;;
    2|"storyboard_content")
        test_args="--tests storyboard_content"
        ;;
    3|"storyboard_process")
        test_args="--tests storyboard_process"
        ;;
    4|"storyboard_images")
        test_args="--tests storyboard_images"
        ;;
    5|"workflow")
        test_args="--tests workflow"
        ;;
    6|"all"|"")
        test_args=""  # 不传递参数，运行所有测试
        ;;
    *)
        echo "未知选项，默认运行脚本创建测试"
        test_args="--tests script"
        ;;
esac

# 运行测试
echo ""
echo "开始运行真实API测试..."
PYTHONPATH=$PROJECT_DIR python -m tests.test_real_workflow $test_args 2>&1 | tee logs/real_test_$(date +%Y%m%d_%H%M%S).log

echo "测试完成!"
echo "测试结果保存在 output/test/ 目录中"
echo "日志文件保存在 logs/ 目录中" 