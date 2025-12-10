#!/bin/bash
# 设置编码为UTF-8（Linux默认多为UTF-8，显式声明防兼容问题）
export LC_ALL=en_US.UTF-8

# 清除终端并设置标题
clear
echo -e "\033]0;AI写标书助手 - 单端口模式\033\\"

# 设置文本颜色（0B对应Linux的36m青色，类似Windows的亮青色）
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # 重置颜色

# 打印标题
echo -e "${CYAN}================================================"
echo -e "      AI写标书助手 - 单端口集成启动"
echo -e "================================================"${NC}
echo -e "\n"


# 1. 检查前端构建文件（Linux路径用/，判断文件存在用-f）
echo -e "检查前端构建文件..."
if [ ! -f "backend/static/index.html" ]; then
    echo -e "${YELLOW}❌ 前端构建文件不存在，正在构建...${NC}"
    echo -e "\n"
    
    # 1.1 构建前端（需确保已安装Node.js/npm）
    echo -e "${CYAN}[1/2] 构建前端...${NC}"
    cd frontend || { echo -e "${RED}❌ 进入frontend目录失败！${NC}"; exit 1; }
    
    # 检查npm是否安装
    # if ! command -v npm &> /dev/null; then
    #     echo -e "${RED}❌ 未检测到npm，请先安装Node.js（sudo apt install nodejs npm）${NC}"
    #     exit 1
    # fi
    
    # 执行前端构建（Linux无call命令，直接运行）
    npm install
    npm run build
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 前端构建失败${NC}"
        read -n 1 -s -r -p "按任意键退出..."
        exit 1
fi
    cd .. # 返回根目录
    
    # 1.2 复制构建文件（Linux用cp -r，--force覆盖已存在文件）
    echo -e "${CYAN}[2/2] 复制构建文件...${NC}"
    
    # 检查Python是否安装
    # if ! command -v python &> /dev/null; then
    #     echo -e "${RED}❌ 未检测到Python3，请先安装（sudo apt install python3）${NC}"
    #     exit 1
    # fi
    PYTHON_BIN=$(which python || true)
    if [ -z "$PYTHON_BIN" ]; then
        # 兜底：用 conda 的路径
        PYTHON_BIN="/home/star/anaconda3/envs/qwen/bin/python"
    fi
    
    # 复制前端build目录到backend/static（--force强制覆盖）
    python3 -c "import shutil; shutil.copytree('frontend/build', 'backend/static', dirs_exist_ok=True)"
    echo -e "${GREEN}✅ 构建完成${NC}"
    echo -e "\n"
else
    echo -e "${GREEN}✅ 前端构建文件已存在${NC}"
    echo -e "\n"
fi


# 2. 启动集成服务
echo -e "${CYAN}🚀 启动集成服务...${NC}"
echo -e "${GREEN}📡 服务地址: http://localhost:8000${NC}"
echo -e "${GREEN}📚 API文档: http://localhost:8000/docs${NC}"
echo -e "\n"
echo -e "${GREEN}✨ 前后端已集成，无CORS问题！${NC}"
echo -e "${CYAN}================================================"${NC}
echo -e "\n"

# 进入backend目录并启动Python服务
cd backend || { echo -e "${RED}❌ 进入backend目录失败！${NC}"; exit 1; }

# 检查Python环境（若用conda，需先激活环境；此处默认系统Python3，可根据实际修改）
# 若用conda环境，需添加：source ~/miniconda3/bin/activate 环境名
python run.py

# 服务关闭提示
echo -e "\n${YELLOW}👋 服务已关闭${NC}"
# read -n 1 -s -r -p "按任意键退出..."