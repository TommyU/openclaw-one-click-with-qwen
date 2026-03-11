#!/usr/bin/env python3
"""
OpenClaw 一键部署脚本
支持 Docker/Podman，自动创建目录、配置和启动服务
"""

import os
import time
import subprocess
import sys
import json
import argparse
from pathlib import Path

# 配置常量
IMAGE_NAME = "ghcr.io/openclaw/openclaw:latest"
DEFAULT_PORT = 18790
CONFIG_DIR = Path(__file__).parent.resolve()

orange_start = "\033[38;5;208m"
blue_start = "\033[38;5;33m"
reset = "\033[0m"


DOCKER_COMPOSE_CONTENT = """services:
  openclaw:
    image: {image}
    container_name: {container_name}
    restart: always
    userns_mode: "keep-id"
    command: ["openclaw", "gateway", "--bind", "lan", "--port", "18789", "--allow-unconfigured"]
    environment:
      - TZ=Asia/Shanghai
      - GATEWAY_TOKEN=1
    volumes:
      - ./config:/app/config:Z
      - ./data:/app/data:Z
      - ./plugins:/app/plugins:Z
      - ./openclaw-data:/home/node/.openclaw:Z
    ports:
      - "{port}:18789"
    deploy:
      resources:
        limits:
          memory: 2G
"""

OPENCLAW_JSON_TEMPLATE = {
    "models": {
        "mode": "merge",
        "providers": {
            "bailian": {
                "baseUrl": "https://coding.dashscope.aliyuncs.com/v1",
                "apiKey": "{api_key}",
                "api": "openai-completions",
                "models": [
                    {"id": "qwen3.5-plus", "name": "qwen3.5-plus", "reasoning": False,
                     "input": ["text", "image"], "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                     "contextWindow": 1000000, "maxTokens": 65536}
                ]
            }
        }
    },
    "agents": {
        "defaults": {
            "model": {"primary": "bailian/qwen3.5-plus"},
            "models": {"bailian/qwen3.5-plus": {}}
        }
    },
    "commands": {
        "native": "auto",
        "nativeSkills": "auto",
        "restart": True,
        "ownerDisplay": "raw"
    },
    "channels": {
        "whatsapp": {
            "enabled": True,
            "dmPolicy": "pairing",
            "allowFrom": ["{phone}"],
            "groupAllowFrom": ["{phone}"],
            "groupPolicy": "allowlist",
            "debounceMs": 0,
            "mediaMaxMb": 50
        }
    },
    "gateway": {
        "controlUi": {
            "dangerouslyAllowHostHeaderOriginFallback": True,
            "allowInsecureAuth": True
        },
        "auth": {
            "mode": "token",
            "token": "1"
        }
    }
}


def print_banner():
    print("=" * 60)
    print("         OpenClaw 一键部署脚本")
    print("=" * 60)


def get_user_input(prompt, default=None):
    """获取用户输入，支持默认值"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()


def check_container_runtime():
    """检查可用的容器运行时"""
    runtimes = []

    # 检查 podman
    try:
        result = subprocess.run(["podman", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            runtimes.append("podman")
            print(f"[OK] Podman: {result.stdout.strip()}")
    except FileNotFoundError:
        pass

    # 检查 docker
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            runtimes.append("docker")
            print(f"[OK] Docker: {result.stdout.strip()}")
    except FileNotFoundError:
        pass

    return runtimes


def check_docker_compose(runtime):
    """检查 docker-compose 或 podman-compose"""
    compose_cmd = None

    # 尝试 compose 插件
    try:
        result = subprocess.run([runtime, "compose", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            compose_cmd = [runtime, "compose"]
            print(f"[OK] {runtime} compose 可用")
            return compose_cmd
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # 尝试独立的 compose 命令
    compose_candidates = ["docker-compose", "podman-compose"]
    for cmd in compose_candidates:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                compose_cmd = [cmd]
                print(f"[OK] {cmd} 可用")
                return compose_cmd
        except FileNotFoundError:
            pass

    return None


def create_directories():
    """创建必要的目录"""
    dirs = ["config", "data", "plugins", "openclaw-data"]
    print("\n[INFO] 创建目录...")
    for d in dirs:
        path = CONFIG_DIR / d
        path.mkdir(exist_ok=True)
        print(f"  [OK] {path}")


def create_openclaw_config(api_key, phone):
    """创建 openclaw.json 配置文件到 openclaw-data 目录"""
    data_dir = CONFIG_DIR / "openclaw-data"
    data_dir.mkdir(exist_ok=True)

    config_path = data_dir / "openclaw.json"

    print("\n[INFO] 创建 openclaw.json 配置文件...")

    # 填充用户输入的配置
    config_content = json.dumps(OPENCLAW_JSON_TEMPLATE, ensure_ascii=False)
    config_content = config_content.replace("{api_key}", api_key)
    config_content = config_content.replace("{phone}", phone)

    config_json = json.loads(config_content)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_json, f, indent=2, ensure_ascii=False)

    print(f"  [OK] {config_path}")


def create_docker_compose_file(runtime, container_name, local_port):
    """创建 docker-compose.yaml 文件"""
    compose_path = CONFIG_DIR / "docker-compose.yaml"

    print("\n[INFO] 创建 docker-compose.yaml...")

    content = DOCKER_COMPOSE_CONTENT.format(
        image=IMAGE_NAME,
        container_name=container_name,
        port=local_port
    )

    with open(compose_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] {compose_path}")


def pull_image(runtime):
    """拉取镜像"""
    print(f"\n[INFO] 拉取镜像 {IMAGE_NAME}...")
    try:
        subprocess.run([runtime, "pull", IMAGE_NAME], check=True)
        print("  [OK] 镜像拉取成功")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] 镜像拉取失败：{e}")
        sys.exit(1)


def start_service(runtime, container_name):
    """启动服务"""
    print(f"\n[INFO] 启动 OpenClaw 服务...")

    # 使用对应的 compose 命令
    if runtime == "podman":
        compose_cmd = ["podman-compose"]
        # 检查是否支持 podman compose 插件形式
        try:
            subprocess.run(["podman", "compose", "version"], capture_output=True, check=True)
            compose_cmd = ["podman", "compose"]
        except subprocess.CalledProcessError:
            pass
    else:
        compose_cmd = ["docker", "compose"]

    try:
        subprocess.run(compose_cmd + ["up", "-d"], cwd=CONFIG_DIR, check=True)
        print("  [OK] 服务启动成功")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] 服务启动失败：{e}")
        sys.exit(1)

def auto_pair(runtime, container_name):
    """启动服务"""
    print(f"\n[INFO] 自动允许本机浏览器访问openclaw gateway...")

    try:
        # exec -it {container_name} openclaw devices approve
        subprocess.run([runtime, "exec", "-it", container_name, "openclaw", "devices", "approve"], cwd=CONFIG_DIR, check=True)
        print("  [OK] 成功")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] 失败：{e}")
        print(f"{orange_start}打开浏览器之后，如果碰到需要配对，则命令行执行： podman exec -it {container_name} openclaw devices approve{reset}")

        sys.exit(1)

def open_url(http_url):
    """启动服务"""
    # print(f"\n[INFO] 自动允许本机浏览器访问openclaw gateway...")
    print(f"访问地址：{blue_start}{http_url}{reset}")
    try:
        # exec -it {container_name} openclaw devices approve
        subprocess.run(["open", http_url], cwd=CONFIG_DIR, check=True)
        print("  [OK] 成功")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] 失败：{e}")
        print(f"{orange_start}打开浏览器之后，如果碰到需要配对，则命令行执行： podman exec -it {container_name} openclaw devices approve{reset}")

        sys.exit(1)


def show_status(runtime, container_name):
    """显示服务状态"""
    print("\n[INFO] 服务状态...")
    try:
        if runtime == "podman":
            subprocess.run(["podman", "ps", "--filter", f"name={container_name}"])
        else:
            subprocess.run(["docker", "ps", "--filter", f"name={container_name}"])
    except subprocess.CalledProcessError:
        pass


def stop_service(runtime, container_name):
    """停止服务"""
    print(f"\n[INFO] 停止 OpenClaw 服务...")

    if runtime == "podman":
        compose_cmd = ["podman-compose"]
        try:
            subprocess.run(["podman", "compose", "version"], capture_output=True, check=True)
            compose_cmd = ["podman", "compose"]
        except subprocess.CalledProcessError:
            pass
    else:
        compose_cmd = ["docker", "compose"]

    try:
        subprocess.run(compose_cmd + ["down"], cwd=CONFIG_DIR, check=True)
        print("  [OK] 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] 停止服务失败：{e}")


def collect_user_config():
    """收集用户配置信息"""
    print("\n" + "-" * 60)
    print("请配置 OpenClaw 所需信息：")
    print("-" * 60)

    # 容器名称
    container_name = get_user_input("容器名称", "my-claw")

    # 本地端口
    local_port = get_user_input("本地映射端口", "18790")

    # API Key
    api_key = get_user_input("千问套餐 https://bailian.console.aliyun.com/cn-beijing/?tab=coding-plan#/efm/detail 【套餐专属API Key】")
    while not api_key:
        print("  [ERROR] API Key 不能为空")
        api_key = get_user_input("千问 API Key (必填)")

    # 手机号
    phone = get_user_input("WhatsApp 手机号 (带国家码，如 +8613800138000)")
    while not phone:
        print("  [ERROR] 手机号不能为空")
        phone = get_user_input("WhatsApp 手机号 (带国家码，如 +8613800138000)")

    return container_name, local_port, api_key, phone


def main():
    parser = argparse.ArgumentParser(description="OpenClaw 一键部署脚本")
    parser.add_argument("--stop", action="store_true", help="停止服务")
    parser.add_argument("--status", action="store_true", help="查看服务状态")
    parser.add_argument("--force", action="store_true", help="强制重新配置")
    args = parser.parse_args()

    print_banner()

    # 检查容器运行时
    runtimes = check_container_runtime()
    if not runtimes:
        print("\n[ERROR] 未找到可用的容器运行时，请安装 Docker 或 Podman")
        sys.exit(1)

    # 优先使用 podman
    runtime = "podman" if "podman" in runtimes else "docker"
    print(f"\n[INFO] 使用容器运行时：{runtime}")

    if args.stop:
        # 从 docker-compose.yaml 读取容器名
        container_name = "my-claw"
        compose_file = CONFIG_DIR / "docker-compose.yaml"
        if compose_file.exists():
            with open(compose_file) as f:
                for line in f:
                    if "container_name:" in line:
                        container_name = line.split(":")[1].strip()
                        break
        stop_service(runtime, container_name)
        return

    if args.status:
        # 从 docker-compose.yaml 读取容器名
        container_name = "my-claw"
        compose_file = CONFIG_DIR / "docker-compose.yaml"
        if compose_file.exists():
            with open(compose_file) as f:
                for line in f:
                    if "container_name:" in line:
                        container_name = line.split(":")[1].strip()
                        break
        show_status(runtime, container_name)
        return

    # 部署流程
    print("\n" + "=" * 60)
    print("开始部署 OpenClaw...")
    print("=" * 60)

    # 收集用户配置
    container_name, local_port, api_key, phone = collect_user_config()

    print(f"\n[INFO] 配置信息:")
    print(f"  - 容器名称：{container_name}")
    print(f"  - 本地端口：{local_port}")
    print(f"  - API Key: {api_key[:10]}...{api_key[-5:]}")
    print(f"  - 手机号：{phone}")

    # 创建目录和配置
    create_directories()
    create_openclaw_config(api_key, phone)
    create_docker_compose_file(runtime, container_name, local_port)
    pull_image(runtime)
    start_service(runtime, container_name)

    show_status(runtime, container_name)

    print("\n" + "=" * 60)
    
    print("部署完成！等待openclaw gateway充分启动... (60秒)")
    time.sleep(60) # 等待openclaw gateway充分启动
    print(f"访问地址：{blue_start}http://127.0.0.1:{local_port}?token=1{reset}")

    open_url(f"http://127.0.0.1:{local_port}?token=1")
    auto_pair(runtime, container_name)



if __name__ == "__main__":
    main()
