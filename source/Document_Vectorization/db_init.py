"""
数据库初始化模块
负责检查必要的数据库表是否存在
"""
import os
import sys
import pymysql
from typing import Dict, Any, List


def check_tables_exist(mysql_config: Dict[str, Any]) -> bool:
    """
    检查必要的表是否存在，如果不存在则报错并终止运行
    
    Args:
        mysql_config: MySQL数据库配置
        
    Returns:
        是否所有表都存在
    """
    required_tables = [
        "doc_file_metadata",
        "doc_document_chunks",
        "doc_named_entities",
        "doc_processing_tasks"
    ]
    
    try:
        # 连接MySQL
        conn = pymysql.connect(**mysql_config)
        cursor = conn.cursor()
        
        # 获取数据库中的所有表
        cursor.execute(f"SHOW TABLES IN {mysql_config['database']}")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        # 检查必要的表是否都存在
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        if missing_tables:
            print(f"错误: 以下必要的表不存在: {', '.join(missing_tables)}")
            print("请确保数据库已正确初始化")
            return False
        
        print("数据库检查成功，所有必要的表都存在")
        return True
        
    except Exception as e:
        print(f"数据库检查失败: {e}")
        return False
def main():
    """主函数"""
    # MySQL配置
    mysql_config = {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", 3306)),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", "password"),
        "database": os.environ.get("MYSQL_DATABASE", "knowledge_base"),
    }
    
    # 检查数据库表是否存在
    if not check_tables_exist(mysql_config):
        sys.exit(1)  # 如果表不存在，终止运行


if __name__ == "__main__":
    main()