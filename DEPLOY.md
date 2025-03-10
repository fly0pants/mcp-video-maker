# 视频生成器部署文档

本文档详细说明了如何将视频生成器项目部署到远程服务器。

## 前置条件

1. 本地环境要求：

   - Python 3.8+
   - rsync
   - sshpass（脚本会自动安装）
   - 已配置的 `.env` 文件

2. 远程服务器要求：
   - CentOS/RHEL 系统（使用 yum 包管理器）
   - 至少 4GB RAM
   - 至少 50GB 磁盘空间
   - 支持 SSH 连接

## 配置说明

1. 确保 `.env` 文件中包含以下配置：

   ```
   ECS_IP=你的服务器IP
   ECS_USERNAME=你的用户名
   ECS_PASSWORD=你的密码
   ```

2. 其他必要的 API 密钥也需要在 `.env` 文件中正确配置。

## 部署步骤

1. 给部署脚本添加执行权限：

   ```bash
   chmod +x deploy.sh
   ```

2. 运行部署脚本：

   ```bash
   ./deploy.sh
   ```

3. 部署脚本会自动执行以下操作：
   - 检查并安装必要的依赖（使用 yum）
   - 创建远程目录结构
   - 同步项目文件到服务器
   - 设置 Python 虚拟环境
   - 安装项目依赖
   - 配置系统服务
   - 启动服务

## 验证部署

1. 检查服务状态：

   ```bash
   sshpass -p $ECS_PASSWORD ssh $ECS_USERNAME@$ECS_IP 'sudo systemctl status video-maker'
   ```

2. 查看服务日志：
   ```bash
   sshpass -p $ECS_PASSWORD ssh $ECS_USERNAME@$ECS_IP 'sudo journalctl -u video-maker -f'
   ```

## 目录结构

部署后的远程服务器目录结构：

```
~/video-maker/
├── api/
├── agents/
├── assets/
├── config/
├── docs/
├── logs/
├── models/
├── output/
├── services/
├── temp/
├── tests/
├── tools/
├── ui/
├── utils/
├── .env
├── main.py
└── requirements.txt
```

## 常见问题处理

1. 如果服务无法启动：

   - 检查日志文件：`/root/video-maker/logs/`
   - 检查系统日志：`sudo journalctl -u video-maker -n 100`
   - 确认所有 API 密钥配置正确
   - 检查 SELinux 状态：`getenforce`（如果是 Enforcing，可能需要配置相应的策略）

2. 如果需要重启服务：

   ```bash
   sshpass -p $ECS_PASSWORD ssh $ECS_USERNAME@$ECS_IP 'sudo systemctl restart video-maker'
   ```

3. 如果需要更新部署：

   - 重新运行 `deploy.sh` 脚本即可
   - 脚本会自动同步最新代码并重启服务

4. 如果遇到权限问题：
   ```bash
   # 检查SELinux状态
   sestatus
   # 如果需要，临时关闭SELinux
   sudo setenforce 0
   # 永久关闭需要编辑配置文件
   sudo vi /etc/selinux/config
   ```

## 安全建议

1. 建议更改默认的 SSH 端口
2. 设置更强的密码
3. 配置防火墙（使用 firewalld）：
   ```bash
   sudo systemctl start firewalld
   sudo firewall-cmd --permanent --add-port=<your-port>/tcp
   sudo firewall-cmd --reload
   ```
4. 定期更新系统和依赖包：
   ```bash
   sudo yum update -y
   ```
5. 建议使用 SSH 密钥而不是密码登录（需要修改部署脚本）

## 维护说明

1. 日志轮转：

   - 系统自动使用 logrotate 管理日志
   - 日志位置：`/root/video-maker/logs/`
   - 配置文件：`/etc/logrotate.d/`

2. 备份建议：

   - 定期备份 `.env` 文件
   - 定期备份 `output` 目录下的生成内容
   - 可以使用 cron 任务自动备份

3. 监控建议：
   - 使用 `top` 或 `htop` 监控系统资源使用情况
   - 监控服务状态：`systemctl status video-maker`
   - 设置日志告警
   - 考虑使用 Prometheus + Grafana 进行更详细的监控

## 联系与支持

如有部署问题，请查看项目文档或提交 Issue。
