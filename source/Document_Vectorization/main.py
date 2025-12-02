"""
文档向量化与索引构建主程序 (Milvus版本)
用于演示如何使用文档切片、向量化和Milvus向量存储
"""
import os
import json
import warnings
import time
import sys
import argparse
import hashlib
from pathlib import Path
try:
    from .document_chunking import DocumentChunker
except ImportError:
    from document_chunking import DocumentChunker

# 导入环境检查模块
try:
    from .check_environment import check_environment
except ImportError:
    from check_environment import check_environment

# 尝试导入其他模块
try:
    from .text_vectorization import TextVectorizer
except ImportError:
    try:
        from text_vectorization import TextVectorizer
    except ImportError:
        TextVectorizer = None

# 不再需要导入VectorIndexer

try:
    from .vector_storage import VectorStorage
except ImportError:
    try:
        from vector_storage import VectorStorage
    except ImportError:
        VectorStorage = None

# 添加上级目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入MySQL数据库配置
try:
    from .db_config import DB_CONFIG
except ImportError:
    from db_config import DB_CONFIG

# MySQL数据库配置 - 直接使用db_config.py中的配置
MYSQL_CONFIG = DB_CONFIG

# 忽略警告
warnings.filterwarnings("ignore")

def calculate_file_hash(file_path):
    """
    计算文件的MD5哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件的MD5哈希值
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_model_exists(model_name, cache_dir=None):
    """
    检查模型是否已经下载到本地缓存
    
    Args:
        model_name: 模型名称
        cache_dir: 自定义缓存目录，如果为None则使用默认的Hugging Face缓存目录
        
    Returns:
        是否存在模型文件
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
                        return True
    
    # 检查默认的Hugging Face缓存目录
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import HFValidationError
        
        try:
            # 尝试获取模型信息，如果成功则表示模型存在
            snapshot_download(model_name, local_files_only=True)
            return True
        except (HFValidationError, OSError):
            return False
    except ImportError:
        # 如果无法导入huggingface_hub，则无法检查
        return False

def process_document(file_path, output_dir=None, build_index=True, index_type="IVF_FLAT", offline_mode=False, skip_processed=True, vectorizer=None):
    """
    处理单个文档，包括切片、向量化和索引构建
    
    Args:
        file_path: 文档路径
        output_dir: 输出目录，默认为source/chunks_output
        build_index: 是否构建索引
        index_type: 索引类型，可选 'FLAT', 'IVF_FLAT', 'IVF_PQ', 'HNSW'
        offline_mode: 是否使用离线模式，不尝试从网络下载模型
        skip_processed: 是否跳过已处理过的文件
    
    Returns:
        处理后的文档切片列表
    """
    # 导入必要的库
    try:
        import torch
        import pandas as pd
        import numpy as np
        torch_available = True
    except ImportError:
        torch_available = False
        print("警告: 无法导入必要的库，某些功能可能不可用")
    
    # 创建输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chunks_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建模型缓存目录（保存在source文件夹下）
    model_cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_cache")
    os.makedirs(model_cache_dir, exist_ok=True)
    
    # 设置环境变量，指定Hugging Face模型缓存目录
    os.environ["TRANSFORMERS_CACHE"] = model_cache_dir
    os.environ["HF_HOME"] = model_cache_dir
    
    # 检查文件是否已处理过
    output_file = os.path.join(output_dir, f"{os.path.basename(file_path)}_chunks.json")
    if skip_processed and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            # 尝试加载已处理的文件内容
            with open(output_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)
                if chunks and len(chunks) > 0:
                    print(f"文件 {os.path.basename(file_path)} 已处理过，跳过处理")
                    return chunks
        except Exception as e:
            print(f"读取已处理文件失败: {e}，将重新处理")
    
    # 读取文档内容
    print(f"正在处理文档: {file_path}")
    content = ""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext in ['.txt', '.md', '.markdown']:
            # 处理文本文件
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        elif file_ext == '.csv':
            # 处理CSV文件
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                content = df.to_string()
            except Exception as e:
                print(f"处理CSV文件失败: {e}")
                return []
        elif file_ext == '.xlsx':
            # 处理Excel文件
            try:
                import pandas as pd
                df = pd.read_excel(file_path)
                content = df.to_string()
            except Exception as e:
                print(f"处理Excel文件失败: {e}")
                return []
        else:
            print(f"不支持的文件类型: {file_ext}")
            return []
    except Exception as e:
        print(f"读取文件失败: {e}")
        return []
    
    if not content:
        print("文档内容为空")
        return []
    
    # 创建文档切片器
    chunker = DocumentChunker()
    
    # 切分文档
    print("正在切分文档...")
    start_time = time.time()
    # 使用正确的方法名，并传递必要的参数
    file_id = int(time.time())  # 使用时间戳作为临时文件ID
    chunks = chunker.chunk_document(content, file_path, file_id)
    print(f"切分完成，共 {len(chunks)} 个切片，耗时: {time.time() - start_time:.2f}秒")
    
    # 添加元数据
    for i, chunk in enumerate(chunks):
        chunk["metadata"] = {
            "source": os.path.basename(file_path),
            "chunk_id": i,
            "file_path": file_path
        }
    
    # 选择向量化模型
    model_name = "shibing624/text2vec-base-chinese"
    
    # 检查模型是否已下载
    if offline_mode:
        if not check_model_exists(model_name, model_cache_dir):
            print(f"警告: 模型 {model_name} 未下载，且处于离线模式，无法进行向量化")
            return chunks
    
    # 如果没有传入向量化器，则创建一个新的
    if vectorizer is None:
        vectorizer = TextVectorizer(model_name=model_name)
    
    # 执行向量化
    print("正在进行向量化...")
    start_time = time.time()
    vectorized_chunks = vectorizer.vectorize(chunks)
    print(f"向量化完成，耗时: {time.time() - start_time:.2f}秒")
    
    # 保存结果
    output_file = os.path.join(output_dir, f"{os.path.basename(file_path)}_chunks.json")
    
    # 将向量转换为列表以便JSON序列化
    for chunk in vectorized_chunks:
        if "vector" in chunk:
            vec = chunk["vector"]
            if hasattr(vec, "tolist"):
                chunk["vector"] = vec.tolist()
            elif isinstance(vec, list):
                pass  # 已经是列表，不需要转换
            else:
                try:
                    chunk["vector"] = list(vec)
                except Exception:
                    print(f"警告: 无法将向量转换为列表，类型: {type(vec)}")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(vectorized_chunks, f, ensure_ascii=False, indent=2)
    
    print(f"处理完成，结果保存到: {output_file}")
    
    # 构建索引
    if build_index:
        print(f"\n开始构建Milvus向量索引...")
        
        # 使用项目目录下的index_files目录作为索引目录（保留用于兼容）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        index_dir = os.path.join(current_dir, "index_files")
        os.makedirs(index_dir, exist_ok=True)
        
        # 为每个chunk添加必要的字段
        file_id = int(time.time())  # 使用时间戳作为文件ID
        
        for i, chunk in enumerate(vectorized_chunks):
            # 添加必要的字段
            chunk["file_id"] = file_id
            chunk["chunk_index"] = i
            
            # 确保有chunk_text字段
            if "text" in chunk:
                chunk["chunk_text"] = chunk["text"]
            elif "content" in chunk:
                chunk["chunk_text"] = chunk["content"]
            else:
                chunk["chunk_text"] = "未知内容"
            
            # 添加chunk_type字段
            chunk["chunk_type"] = "text"
        
        # 初始化向量存储
        print("初始化Milvus向量存储...")
        vector_storage = VectorStorage(mysql_config=MYSQL_CONFIG)
        
        # 计算文件哈希值
        file_hash = calculate_file_hash(file_path)
        
        # 保存文档信息（先获取真实文档ID）
        start_time = time.time()
        try:
            doc_id = vector_storage.save_document_info(file_path, file_hash)
            # 检查doc_id是否为有效正整数
            if doc_id <= 0:
                raise ValueError(f"获取的文档ID无效: {doc_id}")
            print(f"文档信息已保存，文档ID: {doc_id}，耗时: {time.time() - start_time:.2f}秒")
            
            # 保存原始file_id并更新为真实文档ID
            for chunk in vectorized_chunks:
                chunk["original_file_id"] = chunk.get("file_id", "")  # 保存原始file_id
                chunk["file_id"] = doc_id  # 更新为真实文档ID
        except Exception as e:
            print(f"保存文档信息失败: {e}")
            # 使用时间戳作为备选文档ID，确保是正整数
            doc_id = int(time.time() * 1000)  # 使用毫秒级时间戳
            print(f"使用备选文档ID: {doc_id}")
            
            # 仍然需要更新chunk中的file_id字段
            for chunk in vectorized_chunks:
                chunk["original_file_id"] = chunk.get("file_id", "")
                chunk["file_id"] = doc_id
        
        # 存储向量到Milvus
        start_time = time.time()
        updated_chunks = vector_storage.store_vectors(vectorized_chunks)
        print(f"向量存储到Milvus完成，耗时: {time.time() - start_time:.2f}秒")
        
        # 存储元数据到MySQL
        start_time = time.time()
        vector_storage.store_metadata(updated_chunks, doc_id)
        print(f"元数据存储到MySQL完成，耗时: {time.time() - start_time:.2f}秒")
        
        # 执行示例搜索（如果需要）
        # 这里可以添加Milvus搜索示例
        
        # 以下代码已不再使用，因为我们现在使用VectorStorage而不是VectorIndexer
        """
        # 构建索引
        start_time = time.time()
        indexer.build_index(vectors, metadata)
        print(f"Milvus索引构建完成，耗时: {time.time() - start_time:.2f}秒")
        
        # 优化索引
        print("\n执行索引优化...")
        indexer.optimize_index()
        else:
            print("警告: VectorIndexer模块未导入，无法构建Milvus索引")
        """
    
    return vectorized_chunks

def is_file_processed(file_path, output_dir):
    """
    检查文件是否已经被处理过
    
    Args:
        file_path: 文件路径
        output_dir: 输出目录
        
    Returns:
        bool: 如果文件已处理过则返回True，否则返回False
    """
    # 构建输出文件路径
    output_file = os.path.join(output_dir, f"{os.path.basename(file_path)}_chunks.json")
    
    # 检查文件是否存在
    if os.path.exists(output_file):
        # 检查文件是否为空
        if os.path.getsize(output_file) > 0:
            try:
                # 尝试读取文件内容，确保是有效的JSON
                with open(output_file, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                    if chunks and len(chunks) > 0:
                        print(f"文件 {os.path.basename(file_path)} 已处理过，跳过")
                        return True
            except Exception:
                # 如果读取失败，认为文件未处理过或损坏
                pass
    
    return False

def batch_process_documents(directory, output_dir=None, build_index=True, index_type="IVF_FLAT", offline_mode=False, 
                           file_types=None, skip_processed=True):
    """
    批量处理目录中的文档
    
    Args:
        directory: 文档目录
        output_dir: 输出目录
        build_index: 是否构建索引
        index_type: 索引类型
        offline_mode: 是否使用离线模式，不尝试从网络下载模型
        file_types: 要处理的文件类型列表，如果为None则使用默认类型
        skip_processed: 是否跳过已处理过的文件（增量处理）
    """
    # 导入必要的库
    import torch
    if not os.path.exists(directory) or not os.path.isdir(directory):
        print(f"目录不存在: {directory}")
        return
        
    # 创建一个向量化器实例，用于所有文件的处理
    model_name = "shibing624/text2vec-base-chinese"
    model_cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_cache")
    
    # 检查模型是否已下载
    if offline_mode:
        if not check_model_exists(model_name, model_cache_dir):
            print(f"警告: 模型 {model_name} 未下载，且处于离线模式，无法进行向量化")
            return
    
    # 创建向量化器
    print("初始化文本向量化模型...")
    vectorizer = TextVectorizer(model_name=model_name)
    print("文本向量化模型初始化完成")
    
    # 支持的文件类型
    if file_types is None:
        supported_extensions = ['.txt', '.md', '.markdown', '.csv', '.xlsx']
    else:
        supported_extensions = file_types
    
    # 创建输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chunks_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 查找所有支持的文件
    files = []
    for ext in supported_extensions:
        files.extend(list(Path(directory).glob(f"**/*{ext}")))
    
    if not files:
        print(f"在 {directory} 中没有找到支持的文档文件")
        return
    
    print(f"找到 {len(files)} 个文档文件")
    
    # 处理每个文件
    all_chunks = []
    processed_count = 0
    skipped_count = 0
    
    for i, file_path in enumerate(files):
        file_path_str = str(file_path)
        print(f"\n处理文件 {i+1}/{len(files)}: {file_path}")
        
        # 检查文件是否已处理过
        if skip_processed and is_file_processed(file_path_str, output_dir):
            skipped_count += 1
            # 尝试加载已处理的文件内容
            try:
                output_file = os.path.join(output_dir, f"{os.path.basename(file_path_str)}_chunks.json")
                with open(output_file, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                    all_chunks.extend(chunks)
            except Exception as e:
                print(f"读取已处理文件失败: {e}")
            continue
        
        # 对于批量处理，只为最后一个文件构建索引
        should_build_index = build_index and (i == len(files) - 1)
        
        # 处理文档，传递向量化器实例
        chunks = process_document(file_path_str, output_dir, should_build_index, index_type, offline_mode, skip_processed=True, vectorizer=vectorizer)
        if chunks:
            all_chunks.extend(chunks)
            processed_count += 1
    
    print(f"\n处理完成，共处理 {processed_count} 个文件，跳过 {skipped_count} 个已处理文件")
    
    # 如果需要为所有文档构建一个统一的索引
    if build_index and len(files) > 1:
        print("\n为所有文档构建统一Milvus索引...")
        
        # 创建索引目录
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chunks_output")
        index_dir = os.path.join(output_dir, "indices")
        os.makedirs(index_dir, exist_ok=True)
        
        # 为每个chunk添加必要的字段
        for i, chunk in enumerate(all_chunks):
            # 保存原始file_id（如果存在）
            if "file_id" in chunk:
                chunk["original_file_id"] = chunk["file_id"]
            else:
                chunk["original_file_id"] = ""
            
            # 确保有chunk_index字段
            if "chunk_index" not in chunk:
                chunk["chunk_index"] = i
            
            # 确保有chunk_text字段
            if "chunk_text" not in chunk:
                if "text" in chunk:
                    chunk["chunk_text"] = chunk["text"]
                elif "content" in chunk:
                    chunk["chunk_text"] = chunk["content"]
                else:
                    chunk["chunk_text"] = "未知内容"
            
            # 添加chunk_type字段
            if "chunk_type" not in chunk:
                chunk["chunk_type"] = "text"
        
        # 初始化向量存储
        print("初始化Milvus向量存储...")
        vector_storage = VectorStorage(mysql_config=MYSQL_CONFIG)
        
        # 存储向量到Milvus
        start_time = time.time()
        updated_chunks = vector_storage.store_vectors(all_chunks)
        
        # 检查是否有任何chunk成功获取了vector_id
        vectors_stored = any("vector_id" in chunk and chunk["vector_id"] for chunk in updated_chunks)
        if vectors_stored:
            print(f"向量存储到Milvus完成，耗时: {time.time() - start_time:.2f}秒")
        else:
            print(f"向量未存储到Milvus，耗时: {time.time() - start_time:.2f}秒")
            print("Milvus Lite部署，部署文件路径/gemini/code/database/milvus/milvus.db")
        
        # 为批量处理创建一个统一的文档记录
        batch_doc_path = f"batch_processing_{int(time.time())}"
        batch_doc_hash = hashlib.md5(batch_doc_path.encode()).hexdigest()
        try:
            doc_id = vector_storage.save_document_info(batch_doc_path, batch_doc_hash)
            # 检查doc_id是否为有效正整数
            if doc_id <= 0:
                raise ValueError(f"获取的文档ID无效: {doc_id}")
        except Exception as e:
            print(f"保存批量文档信息失败: {e}")
            # 使用时间戳作为备选文档ID，确保是正整数
            doc_id = int(time.time() * 1000)  # 使用毫秒级时间戳
            print(f"使用备选文档ID: {doc_id}")
        
        # 存储元数据到MySQL
        start_time = time.time()
        vector_storage.store_metadata(updated_chunks, doc_id)
        print(f"元数据存储到MySQL完成，耗时: {time.time() - start_time:.2f}秒")
        
        print(f"统一Milvus索引构建完成，包含 {len(all_chunks)} 个向量")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="文档向量化与索引构建工具")
    parser.add_argument("--file", type=str, help="要处理的文件路径，多个文件用逗号分隔")
    parser.add_argument("--dir", type=str, help="要处理的文档目录")
    parser.add_argument("--output", type=str, help="输出目录")
    parser.add_argument("--index-type", type=str, default="FLAT", choices=["FLAT", "IVF_FLAT", "IVF_PQ", "HNSW"], help="索引类型")
    parser.add_argument("--offline", action="store_true", help="离线模式，不尝试从网络下载模型")
    parser.add_argument("--skip-processed", action="store_true", help="跳过已处理过的文件")
    parser.add_argument("--no-index", action="store_true", help="不构建索引")
    args = parser.parse_args()
    
    # 检查环境
    check_environment()
    
    # 设置索引类型
    index_type = args.index_type
    print(f"使用索引类型: {index_type}")
    
    # 检查必要的库是否已安装
    try:
        import transformers
        import pandas
        import pymilvus
    except ImportError as e:
        print(f"错误: 缺少必要的库: {e}")
        print("请安装必要的库: pip install transformers pandas pymilvus[lite]")
        return
    
    # 处理多个文件（用逗号分隔）
    if args.file:
        # 分割逗号分隔的文件路径
        file_paths = [path.strip() for path in args.file.split(',')]
        
        # 处理每个文件
        for file_path in file_paths:
            if os.path.exists(file_path):
                print(f"\n处理文件: {file_path}")
                process_document(file_path, args.output, not args.no_index, index_type, args.offline, args.skip_processed)
            else:
                print(f"文件不存在: {file_path}")
        return
    
    # 处理目录
    if args.dir:
        if os.path.exists(args.dir) and os.path.isdir(args.dir):
            batch_process_documents(args.dir, args.output, not args.no_index, index_type, args.offline, None, args.skip_processed)
        else:
            print(f"目录不存在: {args.dir}")
        return
    
    # 如果没有指定文件或目录，处理默认目录
    print("未指定文件或目录，将处理默认目录")
    
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 只处理knlgdocs目录中的文件
    dataset_dir = os.path.join(project_root, "knlgdocs")
    
    print(f"处理 {dataset_dir} 中的所有txt、csv、xlsx、md文件")
    
    # 支持的文件类型
    supported_extensions = ['.txt', '.md', '.markdown', '.csv', '.xlsx']

    print("\n=== 处理knlgdocs目录中的文件 ===")
    if os.path.exists(dataset_dir):
        # 统一处理所有支持的文件类型
        batch_process_documents(dataset_dir, build_index=True, index_type=index_type,
                               offline_mode=args.offline, file_types=supported_extensions, skip_processed=args.skip_processed)
    else:
        print(f"目录不存在: {dataset_dir}")

if __name__ == "__main__":
    main()