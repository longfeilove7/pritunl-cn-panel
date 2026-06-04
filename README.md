# Pritunl 中文管理面板

Pritunl VPN 服务器的中文 Web 管理界面，通过 API 代理实现，不修改 Pritunl 原始文件。

## 功能

- 📊 仪表盘（服务器/用户/组织统计）
- 🖥️ 服务器管理（创建/删除/启动/停止/重启/全部设置）
- 🏢 组织管理（创建/删除）
- 👥 用户管理（创建/删除/启用/禁用/详情/配置下载）
- 🖧 主机管理
- 🔗 链接管理
- 📱 设备管理
- 👤 管理员管理
- ⚙️ 系统设置（SSO/Let's Encrypt/SMTP等）
- 📋 系统日志 & 审计日志
- 🔐 双因子认证（Google Authenticator）
- 📧 批量添加用户 & 发送邮件
- 📈 带宽监控

## 要求

- Pritunl 已安装并运行
- Python 3.9+（Pritunl 自带）
- Flask（Pritunl 自带）

## 安装

```bash
# 1. 下载
git clone https://github.com/YOUR_USERNAME/pritunl-cn-panel.git
cd pritunl-cn-panel

# 2. 安装到 /opt/pritunl_cn
sudo mkdir -p /opt/pritunl_cn
sudo cp pritunl_cn.py /opt/pritunl_cn/

# 3. 创建 systemd 服务
sudo cat > /etc/systemd/system/pritunl-cn.service << 'EOF'
[Unit]
Description=Pritunl Chinese Panel
After=pritunl.service

[Service]
Type=simple
ExecStart=/usr/lib/pritunl/usr/bin/python3 /opt/pritunl_cn/pritunl_cn.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 4. 启动
sudo systemctl daemon-reload
sudo systemctl enable --now pritunl-cn
```

## 使用

- 中文面板：`http://YOUR_SERVER_IP:8443`
- 原版英文：`https://YOUR_SERVER_IP:443`
- 登录账号与 Pritunl 管理员相同

## 配置

编辑 `/opt/pritunl_cn/pritunl_cn.py` 顶部配置：

```python
PRITUNL_URL = 'https://127.0.0.1:443'  # Pritunl 地址
LISTEN_PORT = 8443                       # 中文面板端口
```

## 管理

```bash
systemctl status pritunl-cn    # 查看状态
systemctl restart pritunl-cn   # 重启
journalctl -u pritunl-cn -f    # 查看日志
```

## 截图

登录页面、仪表盘、服务器管理等界面全中文显示。

## 原理

- 独立 Flask 应用，通过 Pritunl 内部 API 代理所有操作
- 每个用户独立 session，互不影响
- 不修改 Pritunl 原始文件，可随时卸载
- 与英文版可同时登录使用

## License

MIT
