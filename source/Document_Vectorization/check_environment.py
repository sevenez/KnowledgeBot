"""
环境检查脚本
用于检查必要的库和模型是否已安装/下载
"""
import os
import sys
import importlib
import argparse
from pathlib import Path

def check_package(package_name):
    """
    检查Python包是否已安装
    
    Args:
        package_name: 包名
        
    Returns:
        bool: 如果包已安装则返回True，否则返回False
    """
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def check_model_exists(model_name, cache_dir=None):
    """
    检查模型是否已经下载到本地缓存
    
    Args:
        model_name: 模型名称
        cache_dir: 自定义缓存目录，如果为None则使用默认的Hugging Face缓存目录
        
    Returns:
        bool: 是否存在模型文件
    """
    # 检查自定义缓存目录
    if cache_dir is not None and os.path.exists(cache_dir):
        # 将模型名称转换为目录路径格式
        model_dir = model_name.replace("/", "--")
        custom_model_path = os.path.join(cache_dir, "models--" + model_dir)
        
        if os.path.exists(custom_model_path):
            # 检查是否有pytorch_model.bin文件
            for root, dirs, files in os.walk(custom_model_path):
                for file in files:
                    if file == "pytorch_model.bin" or file.startswith("model") and file.endswith(".bin"):
                        print(f"模型 {model_name} 已存在于自定义缓存目录中: {cache_dir}")
                        return True
    
    # 检查默认的Hugging Face缓存目录
    default_cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    
    # 将模型名称转换为目录路径格式
    model_dir = model_name.replace("/", "--")
    
    # 检查模型文件是否存在
    model_path = os.path.join(default_cache_dir, "models--" + model_dir)
    if os.path.exists(model_path):
        # 检查是否有pytorch_model.bin文件
        for root, dirs, files in os.walk(model_path):
            for file in files:
                if file == "pytorch_model.bin" or file.startswith("model") and file.endswith(".bin"):
                    print(f"模型 {model_name} 已存在于默认缓存目录中: {default_cache_dir}")
                    return True
    
    print(f"模型 {model_name} 不在本地缓存中")
    return False

def check_gpu_availability():
    """
    检查是否有可用的GPU
    
    Returns:
        bool: 如果有可用的GPU则返回True，否则返回False
    """
    if check_package('torch'):
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "未知"
            print(f"GPU可用: {device_name} (共{device_count}个设备)")
        else:
            print("GPU不可用，将使用CPU")
        return gpu_available
    else:
        print("未安装PyTorch，无法检查GPU可用性")
        return False

def check_environment():
    """
    检查环境是否满足要求
    
    Returns:
        dict: 环境检查结果
    """
    print("=== 环境检查 ===")
    
    # 检查Python版本
    python_version = sys.version
    print(f"Python版本: {python_version}")
    
    # 检查必要的库
    required_packages = {
        'torch': '用于深度学习模型',
        'transformers': '用于加载和使用预训练模型',
        'pymilvus': '用于Milvus向量数据库操作',
        'pandas': '用于处理CSV和Excel文件'
    }
    
    missing_packages = []
    installed_packages = []
    
    for package, description in required_packages.items():
        if check_package(package):
            installed_packages.append(package)
            # 获取版本号
            if package == 'torch':
                import torch
                version = torch.__version__
            elif package == 'transformers':
                import transformers
                version = transformers.__version__
            elif package == 'pymilvus':
                import pymilvus
                version = pymilvus.__version__
            elif package == 'pandas':
                import pandas
                version = pandas.__version__
            else:
                version = "未知"
            print(f"✓ {package} ({version}) - {description}")
        else:
            missing_packages.append(package)
            print(f"✗ {package} - {description}")
    
    # 检查GPU可用性
    gpu_available = check_gpu_availability()
    
    # 设置默认模型路径，如果是Linux系统则使用特定路径
    import platform
    if platform.system() == "Linux":
        model_name = "gemini/pretrain/bge-m3"
    else:
        model_name = "BAAI/bge-m3"
    model_cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_cache")
    model_exists = check_model_exists(model_name, cache_dir=model_cache_dir)
    
    # 检查文档目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_result_dir = os.path.join(project_root, "knlgdocs", "MD_result")
    dataset_dir = os.path.join(project_root, "knlgdocs")
    
    md_result_exists = os.path.exists(md_result_dir)
    dataset_exists = os.path.exists(dataset_dir)
    
    print(f"\n文档目录检查:")
    print(f"MD_result目录: {'存在' if md_result_exists else '不存在'}")
    print(f"knlgdocs目录: {'存在' if dataset_exists else '不存在'}")
    
    # 检查索引目录
    index_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_files")
    index_exists = os.path.exists(index_dir)
    
    print(f"\n索引目录: {'存在' if index_exists else '不存在'}")
    
    # 返回检查结果
    return {
        "python_version": python_version,
        "installed_packages": installed_packages,
        "missing_packages": missing_packages,
        "gpu_available": gpu_available,
        "model_exists": model_exists,
        "md_result_exists": md_result_exists,
        "dataset_exists": dataset_exists,
        "index_exists": index_exists
    }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="环境检查工具")
    parser.add_argument("--install", action="store_true", help="提示安装缺失的包")
    args = parser.parse_args()
    
    # 执行环境检查
    result = check_environment()
    
    # 如果有缺失的包，提示安装
    if result["missing_packages"] and args.install:
        print("\n=== 安装缺失的包 ===")
        print("请运行以下命令安装缺失的包:")
        for package in result["missing_packages"]:
            print(f"pip install {package}")
    
    # 总结
    print("\n=== 环境检查总结 ===")
    if not result["missing_packages"]:
        print("✓ 所有必要的库已安装")
    else:
        print(f"✗ 缺少 {len(result['missing_packages'])} 个必要的库")
        print(f"  缺失的库: {', '.join(result['missing_packages'])}")
        print("  请安装缺失的库后再运行程序")
    
    if result["model_exists"]:
        print("✓ 模型已下载到本地")
    else:
        print("✗ 模型未下载到本地")
    
    if result["gpu_available"]:
        print("✓ GPU可用，将使用GPU加速")
    else:
        print("! GPU不可用，将使用CPU（处理速度可能较慢）")
    
    if result["md_result_exists"] and result["dataset_exists"]:
        print("✓ 所有文档目录已存在")
    else:
        print("! 部分文档目录不存在，可能影响处理")
    
    # 返回是否可以继续执行
    can_proceed = not result["missing_packages"] and result["model_exists"]
    print(f"\n环境检查{'通过' if can_proceed else '未通过'}，{'可以' if can_proceed else '不建议'}继续执行程序")
    
    return can_proceed

if __name__ == "__main__":
    main()