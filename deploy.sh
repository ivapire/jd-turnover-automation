#!/bin/bash
# 京东自营周转数据处理 - 一键部署脚本
# 使用方法: ./deploy.sh

set -e

echo "===== 京东自营周转数据处理 - 部署脚本 ====="
echo ""

# 检查 git
if ! git --version > /dev/null 2>&1; then
    echo "[错误] 请先安装 git: xcode-select --install"
    exit 1
fi

# 检查 GitHub 远程仓库
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "[提示] 尚未关联 GitHub 远程仓库"
    echo ""
    echo "请按以下步骤操作:"
    echo "1. 在浏览器打开 https://github.com/new"
    echo "2. 创建一个新仓库, 名称填写: jd-turnover-automation"
    echo "3. 不要勾选任何初始化选项 (README, .gitignore 等)"
    echo "4. 创建后, 复制仓库地址 (类似 https://github.com/你的用户名/jd-turnover-automation.git)"
    echo "5. 运行: git remote add origin 你的仓库地址"
    echo ""
    exit 1
fi

# 提交并推送
echo "[1/3] 提交代码..."
git add -A
git diff --cached --quiet && echo "没有变更, 跳过提交" || git commit -m "京东自营周转数据处理 v5 Web版" -m "FastAPI Web应用, 支持上传底表, 自动计算补货量, 输出固定3 Sheet XLSX"

echo "[2/3] 推送到 GitHub..."
git push -u origin main

echo ""
echo "[3/3] 部署到 Render"
echo ""
echo "请打开 https://dashboard.render.com/select-repo"
echo "在列表中找到 jd-turnover-automation 仓库, 点击 Connect"
echo ""
echo "然后填写:"
echo "  Name:           jd-turnover-automation"
echo "  Build Command:  pip install -e ."
echo "  Start Command:  cd src && uvicorn jd_turnover.main:app --host 0.0.0.0 --port \$PORT"
echo "  Free Instance:  Yes"
echo ""
echo "点击 Create Web Service, 等待 2-3 分钟即可!"
echo "===== 完成 ====="
