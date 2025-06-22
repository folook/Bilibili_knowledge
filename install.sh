#!/bin/bash
# 安装脚本

echo "🚀 安装 Bilibili字幕获取服务"
echo "================================"

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: 未找到uv，请先安装uv"
    echo "安装uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
else
    echo "✅ uv已安装: $(uv --version)"
fi

# 检查Python版本
check_python_version() {
    local python_cmd=$1
    if command -v "$python_cmd" &> /dev/null; then
        local version=$($python_cmd --version 2>&1 | sed 's/Python //')
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        
        if [[ $major -eq 3 && $minor -ge 10 ]]; then
            echo "$python_cmd"
            return 0
        fi
    fi
    return 1
}

# 寻找合适的Python版本
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if PYTHON_CMD=$(check_python_version "$cmd"); then
        break
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo "❌ 错误: 未找到Python 3.10+版本，请先安装Python 3.10或更高版本"
    exit 1
fi

python_version=$($PYTHON_CMD --version 2>&1)
echo "✅ 找到合适的Python版本: $python_version (使用命令: $PYTHON_CMD)"

# 初始化uv项目并创建虚拟环境
echo "📦 初始化uv项目并创建虚拟环境 .venv..."
uv venv .venv --python "$PYTHON_CMD"

if [[ $? -eq 0 ]]; then
    echo "✅ 虚拟环境创建成功"
else
    echo "❌ 虚拟环境创建失败"
    exit 1
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source .venv/bin/activate

if [[ $? -eq 0 ]]; then
    echo "✅ 虚拟环境激活成功"
else
    echo "❌ 虚拟环境激活失败"
    exit 1
fi

# 安装依赖
echo "📦 安装项目依赖..."
uv pip install -e .

if [[ $? -eq 0 ]]; then
    echo "✅ 依赖安装成功"
else
    echo "❌ 依赖安装失败"
    exit 1
fi

# 安装开发依赖（可选）
read -p "是否安装开发依赖？(y/n): " install_dev
if [[ $install_dev == "y" || $install_dev == "Y" ]]; then
    echo "📦 安装开发依赖..."
    uv pip install -e ".[dev]"
    if [[ $? -eq 0 ]]; then
        echo "✅ 开发依赖安装成功"
    else
        echo "❌ 开发依赖安装失败"
    fi
fi

# 运行测试
echo "🧪 运行基本测试..."
uv run python test_service.py

echo ""
echo "🎉 安装完成！"
echo ""
echo "使用方法:"
echo "  # 激活虚拟环境："
echo "  source .venv/bin/activate"
echo ""
echo "  # 或者直接使用uv run："
echo "  uv run python main.py \"https://www.bilibili.com/video/BV1bK411W7t8\""
echo ""
echo "更多使用方法请查看 README.md"