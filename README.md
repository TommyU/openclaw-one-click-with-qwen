# OpenClaw 一键部署脚本

使用 Docker/Podman 快速部署 OpenClaw 网关服务。
复制/下载项目到本地，运行deploy.py
```python
python3 deploy.py
```

## 功能特性

- 自动检测 Docker 或 Podman 容器运行时
- 一键创建所需目录和配置文件
- 支持自定义容器名称、端口、API Key 等配置
- 自动启动服务并打开浏览器浏览openclaw control ui 

## 前置要求

- Python 3.6+
- Docker 或 Podman

## 快速开始

```bash
# 运行部署脚本
python3 deploy.py
```

按提示输入以下信息：
- 容器名称（默认：`my-claw`）
- 本地映射端口（默认：`18790`）
- 千问 API Key
- WhatsApp 手机号（带国家码，如 `+8613800138000`）

## 命令行选项

```bash
# 查看服务状态
python3 deploy.py --status

# 停止服务
python3 deploy.py --stop

# 强制重新配置
python3 deploy.py --force
```

## 配置说明

部署后生成的文件结构：

```
./
├── deploy.py              # 部署脚本
├── docker-compose.yaml    # Docker Compose 配置（自动生成）
├── config/                # 配置文件目录
├── data/                  # 数据目录
├── plugins/               # 插件目录
└── openclaw-data/
    └── openclaw.json      # OpenClaw 主配置（自动生成，模型默认用千问；IM默认用WhatsAPP）
```

## 访问服务

部署完成后，浏览器将自动打开访问地址：

```
http://127.0.0.1:{端口}?token=1
```

## 常见问题
### 为啥容器部署
目前来说它权限过高不安全，可能会误删系统文件/其他资料，所以弄一个隔离的环境。影响隔离。

### 环境要求
由于容器至少需要2G内存, 所以物理机需要至少2G以上内存。

### 设备配对
Mac环境的话，脚本已经处理好了，理论上不需要。

其他平台，如果需要手动进行设备配对，在命令行执行：

```bash
# Podman
podman exec -it my-claw openclaw devices approve

# Docker
docker exec -it my-claw openclaw devices approve
```

## TODO
- 购买千问code plan套餐(过程中会引导): [地址](https://bailian.console.aliyun.com/cn-beijing/?tab=coding-plan#/efm/detail)
- 需要下载WhatsApp(需要自己科学上网)， 后续配置：
  - [whatsapp] 注册（支持国内手机）
  - [openclaw] 在openclaw control ui上打开： 控制/频道， 找到WhatsApp频道，点击【show QR】，会显示一个二维码
  - [whatsapp] 关联设备：App右上角 "..." / 已关联的设备 / 扫描上面的二维码，关联设备
  - [whatsapp] 可能要等待1～2分钟，然后跟自己聊，就可以指挥容器里面的openclaw了
