"""
向量存储模块
负责将向量存储到向量数据库中
"""
import os
import sys
import json
import pymysql
import numpy as np
from typing import List, Dict, Any, Optional, Union
import pymysql
from pymysql.cursors import DictCursor
# 添加logger导入
import logging

# 初始化logger
logger = logging.getLogger(__name__)


class VectorStorage:
    """向量存储器，负责将向量存储到向量数据库中"""
    
    def __init__(self, 
                 mysql_config: Dict[str, Any]):
        """
        初始化向量存储器
        
        Args:
            mysql_config: MySQL数据库配置
        """
        self.mysql_config = mysql_config
        self.vector_db = self._init_vector_db()
    
    def _init_vector_db(self) -> Any:
        """
        初始化Milvus Lite向量数据库连接（嵌入式版本）
        
        Returns:
            向量数据库连接对象
        """
        try:
            from pymilvus import connections, utility
            import platform
            print(f"成功导入pymilvus模块")
            
            # 获取当前工作目录作为项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            print(f"项目根目录: {project_root}")
            
            # 使用项目根目录下的database/milvus目录作为Milvus数据存储路径
            milvus_db_path = os.path.join(project_root, "database", "milvus")
            print(f"Milvus数据库目录路径: {milvus_db_path}")
            
            # 确保目录存在
            try:
                os.makedirs(milvus_db_path, exist_ok=True)
                print(f"成功确保Milvus数据目录存在: {milvus_db_path}")
            except Exception as dir_error:
                print(f"创建Milvus数据目录失败: {dir_error}")
                # 如果创建目录失败，尝试使用临时目录
                import tempfile
                milvus_db_path = tempfile.mkdtemp(prefix="milvus_")
                print(f"使用临时目录作为备选: {milvus_db_path}")
            
            # 使用文件模式连接Milvus，需要指定.db文件
            db_file_path = os.path.join(milvus_db_path, "milvus.db")
            print(f"Milvus数据库文件路径: {db_file_path}")
            
            # 创建空的db文件（如果不存在）
            try:
                with open(db_file_path, 'a'):
                    pass
                print(f"成功创建或确认Milvus数据库文件存在: {db_file_path}")
            except Exception as file_error:
                print(f"创建Milvus数据库文件失败: {file_error}")
            
            # 仅支持Linux环境连接
            print("在Linux系统上尝试连接Milvus Lite...")
            
            try:
                # 首先尝试标准文件模式（备选方案，已确认有效）
                print("尝试标准文件模式连接...")
                connections.connect(
                    alias="default",
                    uri=db_file_path
                )
                
                # 测试连接是否正常
                if connections.has_connection("default"):
                    print("成功使用标准文件模式连接到Milvus Lite")
                    return True
                else:
                    print("Milvus连接存在但状态异常")
                    return False
                    
            except Exception as conn_error:
                print(f"标准文件模式连接失败: {str(conn_error)}")
                print(f"详细错误类型: {type(conn_error).__name__}")
                
                # 尝试嵌入式模式作为备选
                try:
                    print("尝试嵌入式模式连接...")
                    connections.connect(
                        alias="default",
                        uri=f"file:{db_file_path}"
                    )
                    if connections.has_connection("default"):
                        print("成功使用嵌入式模式连接到Milvus Lite")
                        return True
                except Exception as alt_error:
                    print(f"嵌入式模式连接也失败: {str(alt_error)}")
                
                # 提供详细的调试信息
                print(f"数据库文件路径: {db_file_path}")
                print(f"文件是否存在: {os.path.exists(db_file_path)}")
                print(f"文件大小: {os.path.getsize(db_file_path) if os.path.exists(db_file_path) else 'N/A'} bytes")
                
                print("请确保在Linux环境下运行，并安装了正确版本的milvus-lite和pymilvus")
                print("尝试: pip install milvus-lite==2.4.0 pymilvus==2.4.0")
                return None
                
        except ImportError as e:
            print(f"未安装pymilvus模块: {e}")
            print("当前Python版本:", sys.version)
            print("请确保在当前Python环境中安装pymilvus: pip install pymilvus")
            return None
        except Exception as e:
            print(f"连接Milvus Lite失败: {str(e)}")
            print(f"详细错误类型: {type(e).__name__}")
            return None
    
    def _get_or_create_collection(self, collection_name: str):
        """
        获取或创建Milvus集合
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Collection: Milvus集合对象
        """
        try:
            from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, utility
            
            # 如果集合已存在，检查其schema是否包含vector字段
            if utility.has_collection(collection_name):
                # 获取现有集合
                collection = Collection(collection_name)
                # 获取集合的schema
                schema = collection.schema
                
                # 检查schema是否包含vector字段
                has_vector_field = any(field.name == "vector" for field in schema.fields)
                
                if not has_vector_field:
                    # 如果集合没有vector字段，则删除重建
                    logger.warning(f"集合 {collection_name} 不包含vector字段，将删除重建")
                    utility.drop_collection(collection_name)
                    # 重新创建集合
                    return self._create_new_collection(collection_name)
                
                # 加载集合
                collection.load()
                return collection
            
            # 创建新集合
            return self._create_new_collection(collection_name)
            
        except Exception as e:
            logger.error(f"创建或获取集合失败: {e}")
            raise e
            
    def _create_new_collection(self, collection_name: str):
        """
        创建新的Milvus集合
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Collection: Milvus集合对象
        """
        from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
        
        # 定义集合字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768),  # 向量维度为768
            FieldSchema(name="chunk_id", dtype=DataType.INT64),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535)
        ]
        
        # 创建集合模式，启用动态字段功能以增强兼容性
        schema = CollectionSchema(
            fields=fields,
            description="Document chunks collection",
            enable_dynamic_field=True  # 启用动态字段，增加兼容性
        )
        
        # 创建集合并加载
        collection = Collection(name=collection_name, schema=schema)
        
        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="vector", index_params=index_params)
        
        # 加载集合
        collection.load()
        
        logger.info(f"成功创建并加载集合: {collection_name}")
        return collection
    
    def store_vectors(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将向量存储到Milvus Lite向量数据库中（嵌入式版本）
        
        Args:
            chunks: 包含向量的切片列表
            
        Returns:
            更新后的切片列表，包含向量ID（如果存储成功）
        """
        if not self.vector_db:
            # 即使连接失败，也提供清晰的Milvus Lite使用信息
            print("Milvus Lite未连接，无法存储向量")
            print(f"Milvus Lite数据文件位置: {os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'milvus', 'milvus.db'))}")
            print("请确保milvus-lite和pymilvus已正确安装: pip install milvus-lite pymilvus")
            # 即使存储失败，也继续执行后续流程
            return chunks
        
        # 存储向量到Milvus
        try:
            # 从chunks中提取向量和元数据
            vectors = [chunk.get("vector") for chunk in chunks]
            metadata_list = [{k: v for k, v in chunk.items() if k != "vector"} for chunk in chunks]
            updated_chunks = self._store_vectors_milvus("document_chunks", vectors, metadata_list)
            return updated_chunks if updated_chunks else chunks
        except Exception as e:
            print(f"存储向量到Milvus Lite时发生错误: {e}")
            print("向量存储失败，但元数据仍会保存到数据库")
            print(f"详细错误类型: {type(e).__name__}")
            # 即使存储失败，也继续执行后续流程
            return chunks
    
    def _store_vectors_milvus(self, collection_name, vectors, metadata_list):
        """
        将向量存储到Milvus数据库
        """
        try:
            # 获取或创建集合
            collection = self._get_or_create_collection(collection_name)
            
            # 准备插入数据
            insert_data = []
            
            # 确保传入的数据是一致的
            num_vectors = len(vectors)
            num_metadata = len(metadata_list)
            
            if num_vectors != num_metadata:
                raise ValueError(f"向量数量({num_vectors})与元数据数量({num_metadata})不匹配")
            
            # 构造插入数据列表
            for i in range(num_vectors):
                vector = vectors[i]
                metadata = metadata_list[i]
                
                # 确保向量是有效的
                if vector is None or not isinstance(vector, (list, np.ndarray)):
                    logger.warning(f"跳过无效向量，索引: {i}")
                    continue
                
                # 确保向量维度为768
                if len(vector) != 768:
                    # 改为调试日志，避免用户困惑
                    logger.debug(f"自动调整向量维度(期望:768，实际:{len(vector)})，索引: {i}")
                    # 如果维度不一致，尝试调整到768维（简单截断或填充）
                    if len(vector) > 768:
                        vector = vector[:768]  # 截断
                    else:
                        # 填充0到768维
                        vector = np.pad(vector, (0, 768 - len(vector)), 'constant').tolist()
                
                # 确保每个字段都是单个值而不是列表
                insert_record = {
                    "vector": vector,
                    "chunk_id": int(metadata.get("chunk_id", i)) if not isinstance(metadata.get("chunk_id"), list) else int(metadata.get("chunk_id")[0]),
                    "doc_id": metadata.get("doc_id") if not isinstance(metadata.get("doc_id"), list) else metadata.get("doc_id")[0],
                    "chunk_index": int(metadata.get("chunk_index", 0)) if not isinstance(metadata.get("chunk_index"), list) else int(metadata.get("chunk_index")[0]),
                    "content": metadata.get("content") if not isinstance(metadata.get("content"), list) else metadata.get("content")[0]
                }
                
                # 处理其他可能的元数据字段，但只添加schema中已定义的字段
                # 这样可以避免插入未在schema中定义的字段而导致的错误
                schema_fields = {field.name for field in collection.schema.fields}
                for key, value in metadata.items():
                    if key in schema_fields and key not in ["chunk_id", "doc_id", "chunk_index", "content", "vector", "id"]:
                        # 确保不是列表，如果是列表则取第一个元素
                        if isinstance(value, list):
                            insert_record[key] = value[0] if value else None
                        else:
                            insert_record[key] = value
                
                insert_data.append(insert_record)
            
            if not insert_data:
                logger.warning("没有有效的向量数据可插入")
                return None
            
            # 执行插入操作
            insert_result = collection.insert(insert_data)
            collection.flush()
            
            logger.info(f"成功插入 {len(insert_result.primary_keys)} 条向量记录到集合 {collection_name}")
            
            # 更新chunks数据，添加向量ID信息
            updated_chunks = []
            for i, chunk in enumerate(metadata_list):
                if i < len(insert_result.primary_keys):
                    # 创建更新后的chunk，包含向量ID
                    updated_chunk = chunk.copy()
                    updated_chunk["vector_id"] = str(insert_result.primary_keys[i])
                    updated_chunks.append(updated_chunk)
                else:
                    # 如果没有对应的向量ID，使用原始chunk
                    updated_chunks.append(chunk)
            
            return updated_chunks
            
        except Exception as insert_error:
            logger.error(f"Milvus插入失败: {insert_error}")
            error_type = type(insert_error).__name__
            logger.error(f"插入错误类型: {error_type}")
            
            # 提供更详细的错误信息和调试建议
            if "DataNotMatchException" in str(type(insert_error)):
                logger.error("可能的原因：集合schema不匹配、向量维度错误或字段类型不匹配")
                logger.error("建议检查集合是否包含正确的字段，特别是vector字段")
                
                # 尝试获取集合信息用于调试
                try:
                    if utility.has_collection(collection_name):
                        collection = Collection(collection_name)
                        schema = collection.schema
                        logger.error(f"当前集合schema: {schema}")
                except Exception:
                    pass
            
            raise insert_error

    def store_metadata(self, chunks: List[Dict[str, Any]], document_id: int) -> None:
        """
        将切片元数据存储到MySQL中
        
        Args:
            chunks: 包含向量ID的切片列表
            document_id: 文档在doc_documents表中的ID
        """
        # 验证document_id是否为有效的正整数
        if not isinstance(document_id, int) or document_id <= 0:
            raise ValueError(f"无效的文档ID: {document_id}，必须是正整数")
        
        try:
            # 连接MySQL
            conn = pymysql.connect(**self.mysql_config, cursorclass=DictCursor)
            cursor = conn.cursor()
            
            # 存储切片元数据
            for i, chunk in enumerate(chunks):
                # 插入切片记录
                # 生成chunk_id: 使用document_id和chunk_index组合
                chunk_id = f"{document_id}_{chunk['chunk_index']}"
                
                # 使用原始file_id，如果不存在则使用document_id
                # 支持多种可能的file_id字段名，确保最终值为字符串
                file_id_to_store = str(
                    chunk.get("original_file_id", "") or 
                    chunk.get("file_id", "") or 
                    document_id  # 使用文档ID作为备选
                )
                
                # 调试信息：只在处理第一个和最后一个chunk时显示，避免过多输出
                if i == 0:
                    print(f"开始处理chunks，总共 {len(chunks)} 个chunks")
                if i == len(chunks) - 1:
                    print(f"最后一个chunk处理完成")
                
                cursor.execute(
                    """
                    INSERT INTO doc_document_chunks 
                    (document_id, file_id, chunk_id, chunk_index, content, vector_id) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document_id,  # document_id 使用文档ID（来自doc_documents表）
                        file_id_to_store,  # file_id 使用原始file_id或document_id
                        chunk_id,
                        chunk["chunk_index"],
                        chunk.get("chunk_text", chunk.get("content", chunk.get("text", ""))),
                        chunk.get("vector_id", "")
                    )
                )
                
                # 插入实体记录（暂时注释，因为doc_named_entities表可能不存在）
                # if "entities" in chunk and chunk["entities"]:
                #     for entity in chunk["entities"]:
                #         cursor.execute(
                #             """
                #             INSERT INTO doc_named_entities 
                #             (chunk_id, entity_text, entity_type) 
                #             VALUES (%s, %s, %s)
                #             """,
                #             (
                #                 chunk_id,
                #                 entity["entity_text"],
                #                 entity["entity_type"]
                #             )
                #         )
            
            # 提交事务
            conn.commit()
            
            # 关闭连接
            cursor.close()
            conn.close()
            
            print(f"成功存储 {len(chunks)} 个chunks的元数据到MySQL")
            
        except Exception as e:
            print(f"存储元数据到MySQL失败: {e}")

    def delete_vectors_by_file_path(self, file_path: str, klg_base_code: str = None) -> bool:
        """
        根据文件路径和知识库编码删除向量记录
        
        Args:
            file_path: 文件路径
            klg_base_code: 知识库编号（可选，如果提供则必须匹配）
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 连接到MySQL数据库
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # 1. 首先查询文档ID（如果提供了知识库编码，则必须匹配）
            if klg_base_code:
                cursor.execute(
                        "SELECT id FROM doc_documents WHERE path = %s AND knlg_base_code = %s",
                        (file_path, klg_base_code)
                    )
            else:
                cursor.execute(
                        "SELECT id FROM doc_documents WHERE path = %s",
                        (file_path,)
                    )
            document = cursor.fetchone()
            
            if not document:
                print(f"未找到文件路径对应的文档: {file_path}")
                return False
                
            document_id = document[0]
            
            # 2. 查询所有相关的切片ID
            cursor.execute(
                "SELECT id FROM doc_document_chunks WHERE file_id = %s",
                (document_id,)
            )
            chunk_ids = [row[0] for row in cursor.fetchall()]
            
            # 3. 删除命名实体记录
            if chunk_ids:
                cursor.execute(
                    "DELETE FROM doc_named_entities WHERE chunk_id IN (%s)" % 
                    ','.join(['%s'] * len(chunk_ids)),
                    chunk_ids
                )
            
            # 4. 删除切片记录
            cursor.execute(
                "DELETE FROM doc_document_chunks WHERE file_id = %s",
                (document_id,)
            )
            
            # 5. 删除文档记录
            cursor.execute(
                "DELETE FROM doc_documents WHERE id = %s",
                (document_id,)
            )
            
            # 6. 如果Milvus Lite已连接，从中删除向量
            if self.vector_db:
                try:
                    from pymilvus import Collection, utility
                    # 注意：确保集合名称与存储时使用的一致
                    collection_name = "document_chunks"
                    
                    if utility.has_collection(collection_name):
                        collection = Collection(collection_name)
                        
                        # 构建查询表达式来删除该文档的所有向量
                        expr = f"file_id == {document_id}"
                        collection.delete(expr)
                        print(f"从Milvus Lite删除文档ID {document_id}的向量")
                    else:
                        print(f"集合 {collection_name} 不存在，无需删除向量")
                except Exception as e:
                    print(f"从Milvus Lite删除向量失败: {e}")
            else:
                print("Milvus Lite未连接，跳过向量删除操作")
            
            # 提交事务
            conn.commit()
            
            # 关闭连接
            cursor.close()
            conn.close()
            
            print(f"成功删除文件路径 {file_path} 的所有向量记录")
            return True
            
        except Exception as e:
            print(f"删除向量记录失败: {e}")
            return False

    def update_document_status(self, file_path: str, status: str) -> bool:
        """
        更新文档状态
        
        Args:
            file_path: 文件路径（唯一标识）
            status: 状态值（'0'-未解析，'1'-已解析，'2'-已向量化）
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 连接MySQL
            conn = pymysql.connect(**self.mysql_config, cursorclass=DictCursor)
            cursor = conn.cursor()
            
            # 更新文档状态 - 确保status参数是字符串类型
            status_str = str(status) if status is not None else '0'
            
            # 更新doc_documents表的status字段
            cursor.execute(
                "UPDATE doc_documents SET status = %s, updated_at = NOW() WHERE path = %s",
                (status_str, file_path)
            )
            docs_affected = cursor.rowcount
            
            # 更新doc_metadata表的status字段
            cursor.execute(
                "UPDATE doc_metadata SET status = %s, update_time = NOW() WHERE file_path = %s",
                (status_str, file_path)
            )
            meta_affected = cursor.rowcount
            
            conn.commit()
            
            cursor.close()
            conn.close()
            
            if docs_affected > 0 or meta_affected > 0:
                logger.info(f"文档状态更新成功: {file_path} -> 状态 {status_str} (doc_documents: {docs_affected}, doc_metadata: {meta_affected})")
                return True
            else:
                logger.warning(f"文档状态更新失败，未找到文件: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"更新文档状态失败: {e}")
            return False

    def save_document_info(self, file_path: str, file_hash: str, knlg_base_code: str = None) -> int:
        """
        保存文档基本信息到documents表
        
        Args:
            file_path: 文件路径
            file_hash: 文件哈希值
            knlg_base_code: 知识库编号
            
        Returns:
            int: 文档ID
        """
        try:
            import os
            from datetime import datetime
            
            # 连接MySQL
            conn = pymysql.connect(**self.mysql_config, cursorclass=DictCursor)
            cursor = conn.cursor()
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_extension = os.path.splitext(file_path)[1]
            
            # 处理批量处理模式下的虚拟文件路径
            if file_path.startswith('batch_processing_'):
                file_size = 0  # 批量处理模式下文件大小为0
                modified_time = datetime.now()  # 使用当前时间
            else:
                file_size = os.path.getsize(file_path)
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # 检查文档是否已存在
            cursor.execute(
                "SELECT id FROM doc_documents WHERE path = %s",
                (file_path,)
            )
            existing_doc = cursor.fetchone()
            
            if existing_doc:
                # 更新现有文档
                try:
                    cursor.execute(
                        """
                        UPDATE doc_documents 
                        SET file_hash = %s, size = %s, modified_time = %s, 
                            is_parsed = TRUE, parsed_at = NOW(), updated_at = NOW(),
                            knlg_base_code = %s
                        WHERE id = %s
                        """,
                        (file_hash, file_size, modified_time, knlg_base_code, existing_doc['id'])
                    )
                except pymysql.err.OperationalError as e:
                    # 如果字段不存在，使用不含knlg_base_code的更新语句
                    if 'Unknown column' in str(e) and 'knlg_base_code' in str(e):
                        print("knlg_base_code字段不存在，使用不含该字段的更新语句")
                        cursor.execute(
                            """
                            UPDATE doc_documents 
                            SET file_hash = %s, size = %s, modified_time = %s, 
                                is_parsed = TRUE, parsed_at = NOW(), updated_at = NOW()
                            WHERE id = %s
                            """,
                            (file_hash, file_size, modified_time, existing_doc['id'])
                        )
                    else:
                        raise e
                
                affected_rows = cursor.rowcount
                document_id = existing_doc['id']
                print(f"更新现有文档记录，文档ID: {document_id}, 影响行数: {affected_rows}")
            else:
                # 检查表是否有knlg_base_code字段
                try:
                    cursor.execute(
                        """
                        INSERT INTO doc_documents 
                        (path, name, extension, file_hash, size, modified_time, is_parsed, parsed_at, knlg_base_code, status)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW(), %s, '0')
                        """,
                        (file_path, file_name, file_extension, file_hash, file_size, modified_time, knlg_base_code)
                    )
                except pymysql.err.OperationalError as e:
                    # 如果字段不存在，使用不含knlg_base_code的插入语句
                    if 'Unknown column' in str(e) and 'knlg_base_code' in str(e):
                        print("knlg_base_code字段不存在，使用不含该字段的插入语句")
                        cursor.execute(
                            """
                            INSERT INTO doc_documents 
                            (path, name, extension, file_hash, size, modified_time, is_parsed, parsed_at, status)
                            VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW(), '0')
                            """,
                            (file_path, file_name, file_extension, file_hash, file_size, modified_time)
                        )
                    else:
                        raise e
                
                affected_rows = cursor.rowcount
                document_id = cursor.lastrowid
                
                print(f"插入新文档，影响行数: {affected_rows}, lastrowid: {document_id}")
                
                # 验证lastrowid是否为有效正整数
                if not document_id or document_id <= 0:
                    print(f"警告: 获取的文档ID无效: {document_id}")
                    # 重新查询获取插入的文档ID
                    cursor.execute(
                        "SELECT id FROM doc_documents WHERE path = %s",
                        (file_path,)
                    )
                    result = cursor.fetchone()
                    if result:
                        document_id = result['id']
                        print(f"通过查询获取文档ID: {document_id}")
                    else:
                        # 使用时间戳作为备选ID
                        import time
                        fallback_id = int(time.time() * 1000)
                        # 确保fallback_id是正整数且不为0
                        if fallback_id <= 0:
                            fallback_id = 1
                        print(f"使用备选文档ID: {fallback_id}")
                        document_id = fallback_id
            
            # 提交事务
            conn.commit()
            
            # 关闭连接
            cursor.close()
            conn.close()
            
            print(f"成功保存文档信息，文档ID: {document_id}")
            return document_id
            
        except Exception as e:
            print(f"保存文档信息失败: {e}")
            # 返回一个有效的文档ID（使用极速时间戳作为备选）
            import time
            fallback_id = int(time.time() * 1000)
            # 确保fallback_id是正整数且不为0
            if fallback_id <= 0:
                fallback_id = 1
            print(f"使用备选文档ID: {fallback_id}")
            return fallback_id