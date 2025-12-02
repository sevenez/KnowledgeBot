"""
向量搜索工具 - Milvus Lite版本
用于在Milvus Lite向量数据库（嵌入式版本）中进行搜索
"""
import os
import sys
import json
import time
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加父目录到系统路径，以便导入其他模块
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# 导入文本向量化模块
try:
    from Document_Vectorization.text_vectorization import TextVectorizer
except ImportError:
    print("无法导入TextVectorizer模块，请确保Document_Vectorization目录中包含text_vectorization.py文件")
    sys.exit(1)

class VectorSearchTool:
    """Milvus向量搜索工具类"""
    
    def __init__(self, model_name=None, use_gpu=True):
        # 设置默认模型路径，如果是Linux系统则使用特定路径
        if model_name is None:
            import platform
            if platform.system() == "Linux":
                model_name = "gemini/pretrain/bge-m3"
            else:
                model_name = "BAAI/bge-m3"
        """
        初始化向量搜索工具
        
        Args:
            model_name: 向量化模型名称
            use_gpu: 是否使用GPU
        """
        self.model_name = model_name
        self.use_gpu = use_gpu and self._check_gpu_available()
        
        # 创建文本向量化器
        print(f"正在加载文本向量化模型: {model_name}")
        self.vectorizer = TextVectorizer(model_name=model_name)
        
        # 初始化Milvus连接
        self.milvus_conn = self._init_milvus_connection()
        
        # 检查集合是否存在
        self.collection_name = "document_chunks"
        self.collection = self._get_collection()
    
    def _check_gpu_available(self):
        """检查是否有可用的GPU"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _init_milvus_connection(self):
        """初始化Milvus连接"""
        try:
            from pymilvus import connections
            
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            milvus_db_path = os.path.join(project_root, "database", "milvus")
            db_file_path = os.path.join(milvus_db_path, "milvus.db")
            
            # 确保目录存在
            os.makedirs(milvus_db_path, exist_ok=True)
            
            # 连接到Milvus
            connections.connect(
                alias="default",
                uri=db_file_path
            )
            
            if connections.has_connection("default"):
                print("成功连接到Milvus数据库")
                return connections.get_connection("default")
            else:
                print("Milvus连接失败")
                return None
                
        except ImportError as e:
            print(f"未安装pymilvus模块: {e}")
            print("请安装: pip install pymilvus")
            return None
        except Exception as e:
            print(f"连接Milvus失败: {e}")
            return None
    
    def _get_collection(self):
        """获取Milvus集合"""
        try:
            from pymilvus import Collection, utility
            
            if not utility.has_collection(self.collection_name):
                print(f"集合 {self.collection_name} 不存在，请先构建索引")
                return None
            
            collection = Collection(self.collection_name)
            collection.load()
            print(f"成功加载集合: {self.collection_name}")
            return collection
            
        except Exception as e:
            print(f"获取集合失败: {e}")
            return None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        在Milvus中搜索最相似的文档
        
        Args:
            query: 查询文本
            top_k: 返回的结果数量
            
        Returns:
            list: 搜索结果列表
        """
        if self.collection is None:
            print("Milvus集合未初始化，无法搜索")
            return []
        
        # 向量化查询
        query_vector = self.vectorizer._encode_texts([query])[0]
        
        # 转换为NumPy数组
        if hasattr(query_vector, "detach"):
            query_vector = query_vector.detach().cpu().numpy()
        
        query_vector = np.array(query_vector, dtype=np.float32)
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)
        
        # 执行搜索
        try:
            from pymilvus import Collection
            
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }
            
            # 执行搜索
            results = self.collection.search(
                data=query_vector,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["chunk_id", "file_id"]
            )
            
            # 处理搜索结果
            search_results = []
            for i, result in enumerate(results[0]):
                # 获取元数据
                chunk_id = result.entity.get("chunk_id")
                file_id = result.entity.get("file_id")
                
                # 从MySQL获取详细元数据
                metadata = self._get_chunk_metadata(chunk_id, file_id)
                if metadata:
                    # 计算相似度分数
                    similarity = 1.0 / (1.0 + result.distance)
                    
                    search_result = {
                        "position": i + 1,
                        "similarity": similarity,
                        "distance": result.distance,
                        "chunk_id": chunk_id,
                        "file_id": file_id,
                        "metadata": metadata
                    }
                    search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def _get_chunk_metadata(self, chunk_id: int, file_id: int) -> Optional[Dict[str, Any]]:
        """从MySQL获取切片元数据"""
        try:
            import pymysql
            from pymysql.cursors import DictCursor
            
            # MySQL配置（需要根据实际配置调整）
            mysql_config = {
                'host': 'localhost',
                'user': 'root',
                'password': 'password',
                'database': 'document_db',
                'charset': 'utf8mb4'
            }
            
            conn = pymysql.connect(**mysql_config, cursorclass=DictCursor)
            cursor = conn.cursor()
            
            # 查询切片信息
            cursor.execute("""
                SELECT dc.chunk_text, dc.chunk_type, d.path as file_path, d.name as file_name
                FROM doc_document_chunks dc
                JOIN doc_documents d ON dc.file_id = d.id
                WHERE dc.id = %s AND dc.file_id = %s
            """, (chunk_id, file_id))
            
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                return {
                    "text": result["chunk_text"],
                    "type": result["chunk_type"],
                    "file_path": result["file_path"],
                    "file_name": result["file_name"],
                    "source": f"{result['file_name']} (chunk {chunk_id})"
                }
            return None
            
        except Exception as e:
            print(f"获取元数据失败: {e}")
            return None

def interactive_search():
    """交互式搜索"""
    print("=== Milvus向量搜索工具 ===")
    
    # 创建搜索工具
    try:
        search_tool = VectorSearchTool()
    except Exception as e:
        print(f"初始化搜索工具失败: {e}")
        return
    
    print("\n搜索工具已准备就绪")
    print("输入'退出'结束搜索")
    
    while True:
        # 获取用户输入
        query = input("\n请输入搜索查询: ")
        if query.lower() in ["退出", "exit", "quit"]:
            print("搜索结束")
            break
        
        # 执行搜索
        start_time = time.time()
        results = search_tool.search(query, top_k=5)
        search_time = time.time() - start_time
        
        # 显示结果
        print(f"\n找到 {len(results)} 个结果 (耗时: {search_time:.3f}秒)")
        
        for i, result in enumerate(results):
            print(f"\n[{i+1}] 相似度: {result['similarity']:.4f}")
            
            # 显示元数据
            meta = result["metadata"]
            if "text" in meta:
                text = meta["text"]
                print(f"内容: {text[:200]}..." if len(text) > 200 else f"内容: {text}")
            
            # 显示来源
            if "source" in meta:
                print(f"来源: {meta['source']}")
            
            # 显示文件路径
            if "file_path" in meta:
                print(f"文件: {meta['file_path']}")

def main():
    """主函数"""
    interactive_search()

if __name__ == "__main__":
    main()