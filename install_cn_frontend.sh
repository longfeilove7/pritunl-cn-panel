#!/bin/bash
# Pritunl 中文版前端安装脚本
# 在服务器上运行此脚本

set -e

echo "=== Pritunl 中文版前端安装 ==="

# 备份原始文件
echo "备份原始文件..."
cp /usr/share/pritunl/www/js/main.cd4c7d0d65fd15965d986d667780081e.js /usr/share/pritunl/www/js/main.cd4c7d0d65fd15965d986d667780081e.js.bak
cp /usr/share/pritunl/www/index.html /usr/share/pritunl/www/index.html.bak

# 复制中文版JavaScript
echo "安装中文版JavaScript..."
cp /opt/pritunl_cn/www/main.cn.js /usr/share/pritunl/www/js/main.cd4c7d0d65fd15965d986d667780081e.js

# 更新index.html（如果需要）
echo "更新index.html..."

# 重启Pritunl服务
echo "重启Pritunl服务..."
systemctl restart pritunl

echo "=== 安装完成 ==="
echo "请访问 https://服务器IP:443 查看中文版界面"
