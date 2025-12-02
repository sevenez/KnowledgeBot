"""
索引构建模块
负责构建和更新向量索引
"""
import os
from typing import Dict, Any, List, Optional


class IndexBuilder:
    """索引构建器，负责构建和更新向量索引"""
    
    def __init__(self, vector_db_type: str = "milvus"):
        """
        初始化索引构建器
        
        Args:
            vector_db_type: 向量数据库类型，支持milvus、pgvector、qdrant
        """
        self.vector_db_type = vector_db_type
    
    def build_index(self, collection_name: str = "document_chunks") -> bool:
        """
        构建向量索引
        
        Args:
            collection_name: 集合名称
            
        Returns:
            是否成功构建索引
        """
        # 根据向量数据库类型构建索引
        if self.vector_db_type == "milvus":
            return self._build_index_milvus(collection_name)
        elif self.vector_db_type == "pgvector":
            return self._build_index_pgvector(collection_name)
        elif self.vector_db_type == "qdrant":
            return self._build_index_qdrant(collection_name)
        else:
            print(f"不支持的向量数据库类型: {self.vector_db_type}")
            return False
    
    def _build_index_milvus(self, collection_name: str) -> bool:
        """
        构建Milvus索引
        
        Args:
            collection_name: 集合名称
            
        Returns:
            是否成功构建索引
        """
        try:
            from pymilvus import Collection, utility
            
            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                print(f"集合 {collection_name} 不存在")
                return False
            
            # 加载集合
            collection = Collection(name=collection_name)
            
            # 检查索引是否已存在
            index_info = collection.index().params
            if index_info:
                print(f"集合 {collection_name} 已有索引: {index_info}")
                # 重建索引
                field_name = "embedding"
                collection.drop_index()
                
                # 创建新索引
                index_params = {
                    "metric_type": "L2",
                    "index_type": "HNSW",
                    "params": {"M": 8, "efConstruction": 64}
                }
                collection.create_index(field_name=field_name, index_params=index_params)
                print(f"重建索引成功: {collection_name}")
            else:
                # 创建索引
                field_name = "embedding"
                index_params = {
                    "metric_type": "L2",
                    "index_type": "HNSW",
                    "params": {"M": 8, "efConstruction": 64}
                }
                collection.create_index(field_name=field_name, index_params=index_params)
                print(f"创建索引成功: {collection_name}")
            
            # 加载集合到内存
            collection.load()
            
            return True
            
        except Exception as e:
            print(f"构建Milvus索引失败: {e}")
            return False
    
    def _build_index_pgvector(self, table_name: str) -> bool:
        """
        构建PGVector索引
        
        Args:
            table_name: 表名
            
        Returns:
            是否成功构建索引
        """
        try:
            import psycopg2
            
            # 连接PostgreSQL
            conn = psycopg2.connect(
                host=os.environ.get("PGVECTOR_HOST", "localhost"),
                port=os.environ.get("PGVECTOR_PORT", "5432"),
                database=os.environ.get("PGVECTOR_DB", "vectordb"),
                user=os.environ.get("PGVECTOR_USER", "postgres"),
                password=os.environ.get("PGVECTOR_PASSWORD", "postgres")
            )
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute(f"SELECT to_regclass('{table_name}')")
            if cursor.fetchone()[0] is None:
                print(f"表 {table_name} 不存在")
                return False
            
            # 检查索引是否已存在
            cursor.execute(f"SELECT indexname FROM pg_indexes WHERE tablename = '{table_name}' AND indexname = '{table_name}_embedding_idx'")
            if cursor.fetchone():
                # 删除旧索引
                cursor.execute(f"DROP INDEX IF EXISTS {table_name}_embedding_idx")
                conn.commit()
                print(f"删除旧索引: {table_name}_embedding_idx")
            
            # 创建新索引
            cursor.execute(f"""
            CREATE INDEX {table_name}_embedding_idx 
            ON {table_name} 
            USING ivfflat (embedding vector_l2_ops)
            WITH (lists = 100)
            """)
            conn.commit()
            print(f"创建索引成功: {table_name}_embedding_idx")
            
            # 关闭连接
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"构建PGVector索引失败: {e}")
            return False
    
    def _build_index_qdrant(self, collection_name: str) -> bool:
        """
        构建Qdrant索引
        
        Args:
            collection_name: 集合名称
            
        Returns:
            是否成功构建索引
        """
        try:
            from qdrant_client import QdrantClient
            
            # 连接Qdrant
            client = QdrantClient(
                url=os.environ.get("QDRANT_URL", "http://localhost:6333")
            )
            
            # 检查集合是否存在
            collections = client.get_collections().collections
            collection_exists = any(collection.name == collection_name for collection in collections)
            
            if not collection_exists:
                print(f"集合 {collection_name} 不存在")
                return False
            
            # Qdrant会自动构建和优化索引，无需手动操作
            print(f"Qdrant自动管理索引，无需手动构建: {collection_name}")
            
            return True
            
        except Exception as e:
            print(f"检查Qdrant索引失败: {e}")
            return False
    
    def update_index(self, collection_name: str = "document_chunks") -> bool:
        """
        更新向量索引
        
        Args:
            collection_name: 集合名称
            
        Returns:
            是否成功更新索引
        """
        # 对于大多数向量数据库，更新索引实际上是重建索引
        return self.build_index(collection_name)