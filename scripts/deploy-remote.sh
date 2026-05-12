#!/usr/bin/env bash
# ===================================
# 远程部署脚本 - daily_stock_analysis
# ===================================
# 目标服务器: root@117.72.39.169
# 部署路径: /data/daily_stock_analysis
# 域名: stock.hao246.cn
#
# 用法:
#   首次部署: ./scripts/deploy-remote.sh init
#   更新部署: ./scripts/deploy-remote.sh update
#   仅更新代码并重启: ./scripts/deploy-remote.sh quick
#   查看 logs: ./scripts/deploy-remote.sh logs
#   重启服务: ./scripts/deploy-remote.sh restart
#   查看状态: ./scripts/deploy-remote.sh status
#   配置 Nginx: ./scripts/deploy-remote.sh nginx
#   完整重置: ./scripts/deploy-remote.sh reset
# ===================================

set -euo pipefail

REMOTE_HOST="root@117.72.39.169"
REMOTE_DIR="/data/daily_stock_analysis"
DOMAIN="stock.hao246.cn"
APP_PORT=8000
COMPOSE_FILE="docker/docker-compose.yml"

ssh_cmd() {
    ssh "$REMOTE_HOST" "$@"
}

info() { echo -e "\033[32m[INFO]\033[0m $*"; }
warn() { echo -e "\033[33m[WARN]\033[0m $*"; }
error() { echo -e "\033[31m[ERROR]\033[0m $*"; exit 1; }

# ===================================
# 首次初始化部署
# ===================================
do_init() {
    info "===== 首次部署初始化 ====="

    # 1. 检查 SSH 连通性
    info "检查 SSH 连接..."
    ssh_cmd "echo 'SSH 连接成功'" || error "无法连接到 $REMOTE_HOST"

    # 2. 安装基础依赖
    info "安装基础依赖..."
    ssh_cmd <<'REMOTE_INIT'
set -e
echo "更新系统包..."
apt-get update -qq

echo "安装 git / curl / docker..."
if ! command -v git &>/dev/null; then
    apt-get install -y -qq git curl
fi

if ! command -v docker &>/dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker 安装完成"
else
    echo "Docker 已安装: $(docker --version)"
fi

if ! command -v docker compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
    echo "安装 Docker Compose 插件..."
    apt-get install -y -qq docker-compose-plugin 2>/dev/null || true
fi

echo "安装 Nginx..."
if ! command -v nginx &>/dev/null; then
    apt-get install -y -qq nginx
    systemctl enable nginx
    systemctl start nginx
else
    echo "Nginx 已安装: $(nginx -v 2>&1)"
fi
REMOTE_INIT

    # 3. 创建目录 & 克隆代码
    info "克隆代码到 $REMOTE_DIR..."
    ssh_cmd <<REMOTE_CLONE
set -e
mkdir -p /data
if [ -d "$REMOTE_DIR/.git" ]; then
    echo "代码目录已存在，跳过克隆"
else
    git clone https://github.com/chenniannian90/daily_stock_analysis.git "$REMOTE_DIR"
    echo "代码克隆完成"
fi
REMOTE_CLONE

    # 4. 配置 .env
    info "检查 .env 配置..."
    ssh_cmd <<REMOTE_ENV
set -e
cd "$REMOTE_DIR"
if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env 已从模板创建，请手动编辑填入 API Key 等配置"
    echo "执行: ssh $REMOTE_HOST 'vim $REMOTE_DIR/.env'"
else
    echo ".env 已存在，跳过"
fi
REMOTE_ENV

    # 5. 配置 Nginx
    do_nginx

    # 6. 构建并启动 Docker
    info "构建并启动 Docker 容器..."
    ssh_cmd <<REMOTE_BUILD
set -e
cd "$REMOTE_DIR"
docker compose -f $COMPOSE_FILE build --no-cache server
docker compose -f $COMPOSE_FILE up -d server
echo "等待服务启动..."
sleep 5
docker compose -f $COMPOSE_FILE ps
REMOTE_BUILD

    info "===== 首次部署完成 ====="
    info ""
    info "后续步骤:"
    info "  1. 编辑 .env:  ssh $REMOTE_HOST 'vim $REMOTE_DIR/.env'"
    info "  2. 重启服务:   $0 restart"
    info "  3. 访问:       http://$DOMAIN"
}

# ===================================
# 更新部署（拉取代码 + 重建 + 重启）
# ===================================
do_update() {
    info "===== 更新部署 ====="

    info "拉取最新代码..."
    ssh_cmd <<REMOTE_UPDATE
set -e
cd "$REMOTE_DIR"
git fetch origin
LOCAL=\$(git rev-parse HEAD)
REMOTE=\$(git rev-parse origin/main)
if [ "\$LOCAL" = "\$REMOTE" ]; then
    echo "代码已是最新 (commit: \${LOCAL:0:8})"
    read -p "是否强制重建镜像? [y/N] " -n 1 -r
    echo
    if [[ ! \$REPLY =~ ^[Yy]\$ ]]; then
        echo "跳过重建，仅重启服务"
        docker compose -f $COMPOSE_FILE restart server
        echo "服务已重启"
        exit 0
    fi
else
    echo "发现新版本:"
    git log --oneline HEAD..origin/main
    git pull origin main
    echo "代码已更新"
fi
REMOTE_UPDATE

    info "重建 Docker 镜像..."
    ssh_cmd <<REMOTE_REBUILD
set -e
cd "$REMOTE_DIR"
docker compose -f $COMPOSE_FILE build server
docker compose -f $COMPOSE_FILE up -d server
echo "等待服务启动..."
sleep 5
docker compose -f $COMPOSE_FILE ps
echo ""
echo "=== 最近日志 ==="
docker compose -f $COMPOSE_FILE logs --tail=20 server
REMOTE_REBUILD

    info "===== 更新完成 ====="
}

# ===================================
# 快速更新（仅拉代码 + 重启，不重建镜像）
# ===================================
do_quick() {
    info "===== 快速更新（仅重启，不重建镜像）====="

    ssh_cmd <<REMOTE_QUICK
set -e
cd "$REMOTE_DIR"
git pull origin main || true
docker compose -f $COMPOSE_FILE restart server
sleep 3
docker compose -f $COMPOSE_FILE ps
REMOTE_QUICK

    info "===== 快速更新完成 ====="
}

# ===================================
# 配置 Nginx 反向代理
# ===================================
do_nginx() {
    info "配置 Nginx 反向代理 ($DOMAIN)..."
    ssh_cmd <<REMOTE_NGINX
set -e
cat > /etc/nginx/conf.d/stock.conf <<'NGINX_CONF'
server {
    listen 80;
    server_name stock.hao246.cn;

    # 安全 headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;

    # 日志
    access_log /var/log/nginx/stock_access.log;
    error_log  /var/log/nginx/stock_error.log;

    # 客户端上传限制（图片识别股票代码等）
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket 支持（Agent 对话页面需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置（LLM 分析可能耗时较长）
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # 缓冲设置
        proxy_buffering off;
    }
}
NGINX_CONF

nginx -t && nginx -s reload
echo "Nginx 配置已更新并重载"
REMOTE_NGINX

    info "Nginx 配置完成: http://$DOMAIN -> http://127.0.0.1:$APP_PORT"
}

# ===================================
# 查看日志
# ===================================
do_logs() {
    info "查看服务日志 (Ctrl+C 退出)..."
    ssh_cmd "cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE logs -f --tail=100 server"
}

# ===================================
# 重启服务
# ===================================
do_restart() {
    info "重启服务..."
    ssh_cmd <<REMOTE_RESTART
set -e
cd "$REMOTE_DIR"
docker compose -f $COMPOSE_FILE restart server
sleep 3
docker compose -f $COMPOSE_FILE ps
REMOTE_RESTART
    info "服务已重启"
}

# ===================================
# 查看状态
# ===================================
do_status() {
    info "查看服务状态..."
    ssh_cmd <<REMOTE_STATUS
set -e
echo "=== Docker 容器状态 ==="
cd "$REMOTE_DIR"
docker compose -f $COMPOSE_FILE ps

echo ""
echo "=== 最近 20 行日志 ==="
docker compose -f $COMPOSE_FILE logs --tail=20 server

echo ""
echo "=== 磁盘使用 ==="
df -h /data

echo ""
echo "=== Git 版本 ==="
cd "$REMOTE_DIR"
git log --oneline -5

echo ""
echo "=== Nginx 状态 ==="
nginx -t 2>&1
systemctl is-active nginx

echo ""
echo "=== 端口监听 ==="
ss -tlnp | grep -E '80|8000'
REMOTE_STATUS
}

# ===================================
# 完整重置（危险操作）
# ===================================
do_reset() {
    warn "===== 完整重置 ====="
    warn "这将删除所有容器、镜像和数据卷！"
    read -p "确认要执行完整重置吗？输入 YES 继续: " -r
    if [ "$REPLY" != "YES" ]; then
        echo "已取消"
        exit 0
    fi

    ssh_cmd <<REMOTE_RESET
set -e
cd "$REMOTE_DIR"
docker compose -f $COMPOSE_FILE down -v --rmi local
echo "容器和镜像已清理"
echo "数据文件保留在 $REMOTE_DIR/data 和 $REMOTE_DIR/logs"
REMOTE_RESET

    info "重置完成。执行 '$0 init' 重新部署。"
}

# ===================================
# 主入口
# ===================================
case "${1:-help}" in
    init)    do_init    ;;
    update)  do_update  ;;
    quick)   do_quick   ;;
    nginx)   do_nginx   ;;
    logs)    do_logs     ;;
    restart) do_restart ;;
    status)  do_status  ;;
    reset)   do_reset   ;;
    *)
        echo "daily_stock_analysis 远程部署工具"
        echo ""
        echo "目标: $REMOTE_HOST:$REMOTE_DIR"
        echo "域名: $DOMAIN"
        echo ""
        echo "用法: $0 <命令>"
        echo ""
        echo "命令:"
        echo "  init      首次部署（安装依赖 + 克隆代码 + 配置 Nginx + 启动服务）"
        echo "  update    更新部署（拉取代码 + 重建镜像 + 重启服务）"
        echo "  quick     快速更新（拉取代码 + 重启，不重建镜像）"
        echo "  nginx     仅配置/更新 Nginx 反向代理"
        echo "  logs      查看服务日志"
        echo "  restart   重启服务"
        echo "  status    查看服务状态"
        echo "  reset     完整重置（删除容器和镜像，保留数据文件）"
        ;;
esac
