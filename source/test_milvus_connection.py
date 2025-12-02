import sys
import os
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 设置工作目录到项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试Milvus Lite连接
def test_milvus_connection():
    # 获取Milvus数据文件路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    milvus_db_path = os.path.join(project_root, 'database', 'milvus')
    db_file_path = os.path.join(milvus_db_path, 'milvus.db')
    
    # 确保目录存在
    os.makedirs(milvus_db_path, exist_ok=True)
    
    print(f"测试Milvus Lite连接...")
    print(f"Milvus数据目录: {milvus_db_path}")
    print(f"Milvus数据文件: {db_file_path}")
    
    # 为Windows系统优化路径格式
    windows_path = db_file_path.replace('\\', '/')
    
    try:
        # 尝试连接Milvus Lite
        connections.connect(
            alias="default",
            uri=windows_path
        )
        
        print(f"成功连接到Milvus Lite")
        print(f"连接状态: {'已连接' if connections.has_connection('default') else '未连接'}")
        
        # 测试创建集合
        print("测试创建集合...")
        
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000)
        ]
        
        # 创建集合
        schema = CollectionSchema(fields=fields, description="测试集合")
        collection = Collection(name="test_collection", schema=schema)
        
        print("成功创建测试集合")
        
        # 插入测试数据
        print("测试插入数据...")
        test_data = [
            [[0.1] * 768],  # 模拟768维向量
            ["测试文本"]
        ]
        
        insert_result = collection.insert(test_data)
        collection.flush()
        
        print(f"成功插入数据，主键ID: {insert_result.primary_keys}")
        
        # 创建向量索引（搜索前必须步骤）
        print("创建向量索引...")
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2", 
            "params": {"nlist": 128}
        }
        collection.create_index("embedding", index_params)
        print("向量索引创建完成")
        
        # 查询数据
        print("测试查询数据...")
        collection.load()
        results = collection.query(expr="id in [" + ",".join(map(str, insert_result.primary_keys)) + "]")
        
        print(f"查询结果: {results}")
        
        # 搜索数据
        print("测试向量搜索...")
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=[[0.1] * 768], 
            anns_field="embedding", 
            param=search_params,
            limit=1,
            output_fields=["text"]
        )
        
        print(f"搜索结果: {results}")
        
        # 删除集合
        collection.drop()
        print("已删除测试集合")
        
        # 断开连接
        connections.disconnect("default")
        print("已断开Milvus Lite连接")
        
        return True
        
    except Exception as e:
        print(f"Milvus Lite连接或操作失败: {str(e)}")
        print(f"详细错误类型: {type(e).__name__}")
        
        # 尝试使用目录路径连接
        try:
            print(f"尝试使用目录路径连接: {milvus_db_path}")
            connections.connect(
                alias="default",
                uri=milvus_db_path
            )
            print(f"成功使用目录路径连接到Milvus Lite")
            connections.disconnect("default")
            return True
        except Exception as e2:
            print(f"使用目录路径连接也失败: {str(e2)}")
            return False

if __name__ == "__main__":
    success = test_milvus_connection()
    print(f"\n测试结果: {'成功' if success else '失败'}")