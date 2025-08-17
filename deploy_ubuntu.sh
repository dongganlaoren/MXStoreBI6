#!/bin/bash
# Ubuntu服务器一键部署脚本
# 使用方法: chmod +x deploy_ubuntu.sh && ./deploy_ubuntu.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
APP_NAME="mixuebi"
APP_USER="ubuntu"
APP_DIR="/home/ubuntu/mixuebi"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    MixueBI Ubuntu服务器部署脚本${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        echo -e "${RED}错误: 请不要使用root用户运行此脚本${NC}"
        echo -e "${YELLOW}建议使用ubuntu用户: sudo -u ubuntu $0${NC}"
        exit 1
    fi
}

# 更新系统包
update_system() {
    echo -e "${YELLOW}[1/10] 更新系统包...${NC}"
    sudo apt update && sudo apt upgrade -y
}

# 安装系统依赖
install_dependencies() {
    echo -e "${YELLOW}[2/10] 安装系统依赖...${NC}"
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        libmysqlclient-dev \
        pkg-config \
        nginx \
        supervisor \
        mysql-server \
        redis-server \
        git \
        curl \
        unzip \
        logrotate
}

# 配置MySQL
setup_mysql() {
    echo -e "${YELLOW}[3/10] 配置MySQL数据库...${NC}"

    # 检查MySQL是否正在运行
    if ! sudo systemctl is-active --quiet mysql; then
        sudo systemctl start mysql
        sudo systemctl enable mysql
    fi

    echo -e "${GREEN}MySQL服务已启动${NC}"
    echo -e "${YELLOW}请手动创建数据库和用户:${NC}"
    echo -e "sudo mysql -u root -p"
    echo -e "CREATE DATABASE mixuebi_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    echo -e "CREATE USER 'mixuebi'@'localhost' IDENTIFIED BY 'your_password';"
    echo -e "GRANT ALL PRIVILEGES ON mixuebi_prod.* TO 'mixuebi'@'localhost';"
    echo -e "FLUSH PRIVILEGES;"
    echo -e "EXIT;"
}

# 创建应用目录
setup_directories() {
    echo -e "${YELLOW}[4/10] 创建应用目录...${NC}"

    mkdir -p $APP_DIR
    mkdir -p $LOG_DIR
    mkdir -p $APP_DIR/app/static/uploads

    # 设置权限
    chmod 755 $APP_DIR
    chmod 755 $LOG_DIR
    chmod 777 $APP_DIR/app/static/uploads
}

# 创建Python虚拟环境
setup_python_env() {
    echo -e "${YELLOW}[5/10] 创建Python虚拟环境...${NC}"

    cd $APP_DIR
    python3 -m venv $VENV_DIR
    source $VENV_DIR/bin/activate

    # 升级pip
    pip install --upgrade pip

    # 安装依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
}

# 配置应用环境变量
setup_env_config() {
    echo -e "${YELLOW}[6/10] 配置环境变量...${NC}"

    cat > $APP_DIR/.env << EOF
# 生产环境配置
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 32)

# 数据库配置
DATABASE_URL=mysql+pymysql://mixuebi:your_password@localhost/mixuebi_prod

# 监控系统配置
MONITORING_ENABLED=True
MONITORING_DATA_RETENTION_DAYS=30
MONITORING_METRICS_RETENTION_DAYS=7
MONITORING_ALERT_EMAIL_ENABLED=True
MONITORING_ALERT_RECIPIENTS=admin@yourdomain.com

# 邮件配置
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com

# 分页配置
RECORDS_PER_PAGE=20
EOF

    echo -e "${GREEN}环境配置文件已创建: $APP_DIR/.env${NC}"
    echo -e "${RED}请根据实际情况修改数据库密码和邮件配置${NC}"
}

# 配置Nginx
setup_nginx() {
    echo -e "${YELLOW}[7/10] 配置Nginx...${NC}"

    # 复制Nginx配置
    sudo cp config_templates/nginx_mixuebi.conf /etc/nginx/sites-available/$APP_NAME

    # 创建软链接
    sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/$APP_NAME

    # 删除默认配置
    sudo rm -f /etc/nginx/sites-enabled/default

    # 测试Nginx配置
    sudo nginx -t

    # 重启Nginx
    sudo systemctl restart nginx
    sudo systemctl enable nginx

    echo -e "${GREEN}Nginx配置完成${NC}"
}

# 配置Supervisor
setup_supervisor() {
    echo -e "${YELLOW}[8/10] 配置Supervisor...${NC}"

    # 复制Supervisor配置
    sudo cp config_templates/supervisor_mixuebi.conf /etc/supervisor/conf.d/$APP_NAME.conf

    # 重新加载Supervisor配置
    sudo supervisorctl reread
    sudo supervisorctl update

    # 启动应用
    sudo supervisorctl start $APP_NAME:*

    echo -e "${GREEN}Supervisor配置完成${NC}"
}

# 设置systemd服务
setup_systemd() {
    echo -e "${YELLOW}[9/10] 配置systemd服务...${NC}"

    # 复制systemd服务文件
    sudo cp config_templates/mixuebi.service /etc/systemd/system/

    # 重新加载systemd
    sudo systemctl daemon-reload

    # 启用服务
    sudo systemctl enable mixuebi.service

    echo -e "${GREEN}systemd服务配置完成${NC}"
}

# 配置日志轮转
setup_logrotate() {
    echo -e "${YELLOW}[10/10] 配置日志轮转...${NC}"

    sudo tee /etc/logrotate.d/mixuebi > /dev/null << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        sudo supervisorctl restart $APP_NAME:*
    endscript
}

/var/log/nginx/mixuebi_*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        sudo systemctl reload nginx
    endscript
}
EOF

    echo -e "${GREEN}日志轮转配置完成${NC}"
}

# 运行数据库迁移
run_migrations() {
    echo -e "${YELLOW}运行数据库迁移...${NC}"

    cd $APP_DIR
    source $VENV_DIR/bin/activate

    export FLASK_APP=run.py
    flask db upgrade

    # 初始化监控系统
    flask init-monitoring

    echo -e "${GREEN}数据库迁移完成${NC}"
}

# 显示部署状态
show_status() {
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${GREEN}     部署完成！服务状态检查${NC}"
    echo -e "${BLUE}===========================================${NC}"

    echo -e "${YELLOW}Nginx状态:${NC}"
    sudo systemctl status nginx --no-pager -l

    echo -e "\n${YELLOW}Supervisor状态:${NC}"
    sudo supervisorctl status

    echo -e "\n${YELLOW}MySQL状态:${NC}"
    sudo systemctl status mysql --no-pager -l

    echo -e "\n${YELLOW}应用健康检查:${NC}"
    cd $APP_DIR
    source $VENV_DIR/bin/activate
    flask test-monitoring

    echo -e "\n${GREEN}部署完成！请访问您的域名查看应用${NC}"
    echo -e "${YELLOW}监控面板地址: https://your-domain.com/monitor${NC}"
}

# 主函数
main() {
    check_root

    echo -e "${YELLOW}开始部署流程...${NC}"

    update_system
    install_dependencies
    setup_mysql
    setup_directories
    setup_python_env
    setup_env_config
    setup_nginx
    setup_supervisor
    setup_systemd
    setup_logrotate
    run_migrations
    show_status

    echo -e "${GREEN}部署完成！${NC}"
}

# 运行主函数
main "$@"
