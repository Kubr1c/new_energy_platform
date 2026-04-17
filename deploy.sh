#!/bin/bash

# 新能源储能系统部署脚本
# 适用于生产环境部署

set -e

echo "=== 新能源储能系统部署脚本 ==="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_NAME="new_energy"
PROJECT_DIR="/opt/$PROJECT_NAME"
BACKUP_DIR="/opt/backups/$PROJECT_NAME"
NGINX_CONF="/etc/nginx/sites-available/$PROJECT_NAME"
SERVICE_FILE="/etc/systemd/system/$PROJECT_NAME.service"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
   echo -e "${RED}请使用root权限运行此脚本${NC}"
   exit 1
fi

# 创建项目目录
echo -e "${YELLOW}1. 创建项目目录...${NC}"
mkdir -p $PROJECT_DIR
mkdir -p $BACKUP_DIR
mkdir -p /var/log/$PROJECT_NAME

# 安装系统依赖
echo -e "${YELLOW}2. 安装系统依赖...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv nodejs npm nginx mysql-server

# 设置MySQL
echo -e "${YELLOW}3. 配置MySQL数据库...${NC}"
if ! systemctl is-active --quiet mysql; then
    systemctl start mysql
    systemctl enable mysql
fi

# 创建数据库和用户
mysql -u root -p <<EOF
CREATE DATABASE IF NOT EXISTS energy_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'energy_user'@'localhost' IDENTIFIED BY 'secure_password_123';
GRANT ALL PRIVILEGES ON energy_db.* TO 'energy_user'@'localhost';
FLUSH PRIVILEGES;
EOF

# 部署后端
echo -e "${YELLOW}4. 部署后端服务...${NC}"
cd $PROJECT_DIR

# 复制后端代码
cp -r backend/* .

# 创建Python虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量
cat > .env <<EOF
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=mysql+pymysql://energy_user:secure_password_123@localhost/energy_db
EOF

# 初始化数据库
python init_db.py

# 生成示例数据
python generate_sample_data.py

# 创建systemd服务
echo -e "${YELLOW}5. 创建系统服务...${NC}"
cat > $SERVICE_FILE <<EOF
[Unit]
Description=New Energy Dispatch System
After=network.target mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$PROJECT_NAME

[Install]
WantedBy=multi-user.target
EOF

# 启动并启用服务
systemctl daemon-reload
systemctl start $PROJECT_NAME
systemctl enable $PROJECT_NAME

# 部署前端
echo -e "${YELLOW}6. 部署前端应用...${NC}"
cd $PROJECT_DIR

# 复制前端代码
cp -r frontend/* frontend_build

# 安装Node.js依赖并构建
cd frontend_build
npm install
npm run build

# 配置Nginx
echo -e "${YELLOW}7. 配置Nginx...${NC}"
cat > $NGINX_CONF <<EOF
server {
    listen 80;
    server_name your-domain.com;  # 替换为实际域名
    
    # 前端静态文件
    location / {
        root $PROJECT_DIR/frontend_build/dist;
        try_files \$uri \$uri/ /index.html;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 启用Nginx配置
ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
systemctl enable nginx

# 配置SSL证书（可选）
echo -e "${YELLOW}8. 配置SSL证书（可选）...${NC}"
read -p "是否配置SSL证书？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    apt-get install -y certbot python3-certbot-nginx
    certbot --nginx -d your-domain.com  # 替换为实际域名
fi

# 配置防火墙
echo -e "${YELLOW}9. 配置防火墙...${NC}"
ufw --force enable
ufw allow ssh
ufw allow 'Nginx Full'

# 设置备份脚本
echo -e "${YELLOW}10. 设置备份脚本...${NC}"
cat > /usr/local/bin/backup_$PROJECT_NAME.sh <<EOF
#!/bin/bash
# 备份脚本

DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="\$BACKUP_DIR/backup_\$DATE.tar.gz"

# 备份数据库
mysqldump -u energy_user -p'secure_password_123' energy_db > \$BACKUP_DIR/db_\$DATE.sql

# 备份项目文件
tar -czf \$BACKUP_FILE \\
    $PROJECT_DIR/.env \\
    $PROJECT_DIR/models_saved/ \\
    \$BACKUP_DIR/db_\$DATE.sql

# 删除7天前的备份
find \$BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete
find \$BACKUP_DIR -name "db_*.sql" -mtime +7 -delete

echo "备份完成: \$BACKUP_FILE"
EOF

chmod +x /usr/local/bin/backup_$PROJECT_NAME.sh

# 添加定时备份任务
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup_$PROJECT_NAME.sh") | crontab -

# 设置日志轮转
echo -e "${YELLOW}11. 配置日志轮转...${NC}"
cat > /etc/logrotate.d/$PROJECT_NAME <<EOF
/var/log/$PROJECT_NAME/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload $PROJECT_NAME
    endscript
}
EOF

# 设置权限
echo -e "${YELLOW}12. 设置文件权限...${NC}"
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 777 $PROJECT_DIR/data
chmod -R 777 $PROJECT_DIR/models_saved

# 验证部署
echo -e "${YELLOW}13. 验证部署...${NC}"
sleep 5

# 检查服务状态
if systemctl is-active --quiet $PROJECT_NAME; then
    echo -e "${GREEN}✓ 后端服务运行正常${NC}"
else
    echo -e "${RED}✗ 后端服务启动失败${NC}"
    systemctl status $PROJECT_NAME
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx服务运行正常${NC}"
else
    echo -e "${RED}✗ Nginx服务启动失败${NC}"
    systemctl status nginx
fi

# 显示部署信息
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo -e "项目目录: ${GREEN}$PROJECT_DIR${NC}"
echo -e "备份目录: ${GREEN}$BACKUP_DIR${NC}"
echo -e "服务状态: ${GREEN}systemctl status $PROJECT_NAME${NC}"
echo -e "Nginx配置: ${GREEN}$NGINX_CONF${NC}"
echo -e "日志文件: ${GREEN}/var/log/$PROJECT_NAME/${NC}"
echo -e "备份脚本: ${GREEN}/usr/local/bin/backup_$PROJECT_NAME.sh${NC}"

echo -e "\n${YELLOW}默认账户信息:${NC}"
echo -e "管理员: ${GREEN}admin / admin123${NC}"
echo -e "操作员: ${GREEN}operator / operator123${NC}"
echo -e "查看者: ${GREEN}viewer / viewer123${NC}"

echo -e "\n${YELLOW}下一步操作:${NC}"
echo -e "1. 修改Nginx配置中的域名"
echo -e "2. 配置SSL证书（生产环境推荐）"
echo -e "3. 上传真实数据到系统"
echo -e "4. 训练预测模型"
echo -e "5. 配置监控和告警"

echo -e "\n${GREEN}部署成功！系统已启动运行。${NC}"
