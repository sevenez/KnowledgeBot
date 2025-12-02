#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI服务启动脚本
提供多种启动方式和配置选项
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def main():
    """主函数，解析命令行参数并启动服务"""
    parser = argparse.ArgumentParser(description='启动FastAPI文件处理服务')
    parser.add_argument('--host', default='0.0.0.0', help='服务监听地址')
    parser.add_argument('--port', type=int, default=8271, help='服务监听端口')
    parser.add_argument('--reload', action='store_true', help='启用热重载（开发模式）')
    parser.add_argument('--workers', type=int, default=1, help='工作进程数量')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("FastAPI文件处理服务")
    print("=" * 60)
    print(f"服务地址: http://{args.host}:{args.port}")
    print(f"API文档: http://{args.host}:{args.port}/docs")
    print(f"热重载: {'启用' if args.reload else '禁用'}")
    print(f"工作进程: {args.workers}")
    print("=" * 60)
    
    # 构建uvicorn命令
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", args.host,
        "--port", str(args.port),
        "--workers", str(args.workers),
        "--log-level", "info",
        "--app-dir", str(current_dir)  # 设置应用目录
    ]
    
    if args.reload:
        cmd.append("--reload")
    
    # 使用subprocess运行命令（Windows兼容），设置工作目录为项目根目录
    try:
        # 获取项目根目录（当前文件的父目录的父目录）
        project_root = current_dir.parent.parent
        subprocess.run(cmd, check=True, cwd=str(project_root))
    except subprocess.CalledProcessError as e:
        print(f"服务启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n服务已停止")

if __name__ == "__main__":
    main()