#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI客户端示例
提供调用API服务的Python客户端类
"""

import requests
import time
import json
from typing import Optional, Dict, Any
from pathlib import Path

class FastAPIClient:
    """FastAPI服务客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8271"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def process_file(self, file_path: str, wait_time: int = 30) -> Dict[str, Any]:
        """
        处理单个文件
        
        Args:
            file_path: 文件完整路径
            wait_time: 等待时间（秒）
            
        Returns:
            处理结果字典
        """
        url = f"{self.base_url}/process"
        payload = {
            "file_path": file_path,
            "wait_time": wait_time
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"请求失败: {str(e)}"
            }
    
    def get_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典
        """
        url = f"{self.base_url}/status/{task_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {
                "error": f"获取状态失败: {str(e)}"
            }
    
    def list_tasks(self) -> Dict[str, Any]:
        """
        获取所有任务列表
        
        Returns:
            任务列表字典
        """
        url = f"{self.base_url}/tasks"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {
                "error": f"获取任务列表失败: {str(e)}"
            }
    
    def wait_for_completion(self, task_id: str, check_interval: int = 5, timeout: int = 300) -> Dict[str, Any]:
        """
        等待任务完成
        
        Args:
            task_id: 任务ID
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒）
            
        Returns:
            最终任务状态
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_status(task_id)
            
            if "error" in status:
                return status
                
            if status["status"] in ["completed", "failed", "error"]:
                return status
                
            print(f"任务 {task_id} 状态: {status['status']} - {status['message']}")
            time.sleep(check_interval)
        
        return {
            "error": f"任务超时，等待时间超过 {timeout} 秒",
            "task_id": task_id
        }

def example_usage():
    """使用示例"""
    client = FastAPIClient()
    
    # 示例文件路径（请替换为实际文件路径）
    file_path = "e:/AIstydycode/AIE/Gitee_EKBQA/knlgdocs/产研部/txt/示例文档.txt"
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"文件不存在: {file_path}")
        print("请提供有效的文件路径")
        return
    
    print("开始处理文件...")
    
    # 启动文件处理
    result = client.process_file(file_path, wait_time=30)
    
    if result.get("success"):
        task_id = result["task_id"]
        print(f"任务已启动，任务ID: {task_id}")
        
        # 等待任务完成
        final_status = client.wait_for_completion(task_id)
        
        if "error" in final_status:
            print(f"任务失败: {final_status['error']}")
        else:
            print(f"任务完成状态: {final_status['status']}")
            print(f"结果文件: {final_status.get('result_path', '无')}")
            print(f"处理消息: {final_status['message']}")
    else:
        print(f"启动处理失败: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    example_usage()