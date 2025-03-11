#!/bin/bash

# 设置错误处理
set -e

# 显示测试信息
echo "======================================"
echo "      视频生成系统完整测试工具        "
echo "======================================"
echo ""

# 激活Python虚拟环境
echo "激活 Python 虚拟环境..."
source .venv/bin/activate

# 检查是否成功激活
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "错误: 无法激活虚拟环境，请确认 .venv 目录存在"
    exit 1
fi

# 检查工作目录
PROJECT_ROOT="$(pwd)"
echo "项目目录: $PROJECT_ROOT"

# 创建必要的目录
mkdir -p output/test
mkdir -p logs

# 运行测试
echo "开始运行完整工作流测试..."
python tests/test_full_workflow.py 2>&1 | tee logs/full_test_$(date +%Y%m%d_%H%M%S).log

# 检查测试结果
if [ $? -eq 0 ]; then
    echo "测试完成: 成功!"
    echo "测试结果保存在 output/test/ 目录中"
    echo "日志文件保存在 logs/ 目录中"
else
    echo "测试完成: 失败!"
    echo "请检查日志文件以获取详细信息"
fi

# 清理
deactivate 