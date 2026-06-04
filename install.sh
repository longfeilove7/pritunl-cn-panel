#!/bin/bash
# Pritunl 中文管理面板 - 一键安装脚本
set -e

echo "========================================="
echo "  Pritunl 中文管理面板 - 安装"
echo "========================================="

# 检查 Pritunl
if ! systemctl is-active pritunl &>/dev/null; then
    echo "错误: Pritunl 未运行，请先安装 Pritunl"
    exit 1
fi

# 检查 Python
PYTHON="/usr/lib/pritunl/usr/bin/python3"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

# 安装
echo ">>> 安装文件..."
mkdir -p /opt/pritunl_cn
cp pritunl_cn.py /opt/pritunl_cn/

# 创建服务
echo ">>> 创建 systemd 服务..."
cat > /etc/systemd/system/pritunl-cn.service << EOF
[Unit]
Description=Pritunl Chinese Panel
After=pritunl.service

[Service]
Type=simple
ExecStart=$PYTHON /opt/pritunl_cn/pritunl_cn.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 启动
echo ">>> 启动服务..."
systemctl daemon-reload
systemctl enable --now pritunl-cn

sleep 3

# 验证
if systemctl is-active pritunl-cn &>/dev/null; then
    echo ""
    echo "========================================="
    echo "  安装成功！"
    echo "  中文面板: http://$(hostname -I | awk '{print $1}'):8443"
    echo "  原版英文: https://$(hostname -I | awk '{print $1}'):443"
    echo "========================================="
else
    echo "安装失败，请检查日志: journalctl -u pritunl-cn -n 20"
    exit 1
fi
