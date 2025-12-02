#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件扫描器
扫描指定目录下的所有文件，并将文件信息记录到MySQL数据库中
支持全量更新（清空表）和增量更新模式
"""

import os
import sys
import hashlib
import logging
import argparse
import datetime
import mysql.connector
from mysql.connector import Error

# 添加父目录到系统路径，以便导入db_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_config import DB_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FileScanner')

class FileScanner:
    """文件扫描器类，用于扫描文件并将信息存入数据库"""
    
    def __init__(self, scan_dir, clear_table=True):
        """
        初始化文件扫描器
        
        Args:
            scan_dir (str): 要扫描的目录路径
            clear_table (bool): 是否在扫描前清空表，默认为True
        """
        self.scan_dir = scan_dir
        self.clear_table = clear_table
        self.conn = None
        self.cursor = None
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        
        # 连接数据库
        self._connect_db()
        
        # 如果设置了清空表，则执行清空操作
        if self.clear_table:
            self._clear_table()
            logger.info("使用全量更新模式（已清空表）")
        else:
            logger.info("使用增量更新模式（保留现有记录）")
    
    def _connect_db(self):
        """连接到MySQL数据库"""
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            logger.info(f"成功连接到数据库 {DB_CONFIG['database']}")
        except Error as e:
            logger.error(f"数据库连接失败: {e}")
            sys.exit(1)
    
    def _clear_table(self):
        """清空documents表"""
        try:
            self.cursor.execute("TRUNCATE TABLE doc_documents")
            self.conn.commit()
            logger.info("已清空documents表")
        except Error as e:
            logger.error(f"清空表失败: {e}")
            self.conn.rollback()
    
    def _calculate_file_hash(self, file_path):
        """
        计算文件的MD5哈希值
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            str: 文件的MD5哈希值
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希值失败 {file_path}: {e}")
            return None
    
    def _get_relative_path(self, abs_path):
        """
        获取相对于项目根目录的相对路径
        
        Args:
            abs_path (str): 绝对路径
            
        Returns:
            str: 相对路径
        """
        return os.path.relpath(abs_path, self.base_dir)
    
    def _file_exists_in_db(self, rel_path):
        """
        检查文件是否已存在于数据库中
        
        Args:
            rel_path (str): 文件的相对路径
            
        Returns:
            bool: 如果文件存在于数据库中则返回True，否则返回False
        """
        try:
            query = "SELECT id FROM doc_documents WHERE path = %s"
            self.cursor.execute(query, (rel_path,))
            result = self.cursor.fetchone()
            return result is not None
        except Error as e:
            logger.error(f"检查文件是否存在失败: {e}")
            return False
    
    def _insert_file(self, file_info):
        """
        将文件信息插入数据库
        
        Args:
            file_info (dict): 包含文件信息的字典
        """
        try:
            query = """
            INSERT INTO doc_documents (path, name, file_type, file_size, 
                                  last_modified, file_hash, is_parsed, parsed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                file_info['path'],
                file_info['file_name'],
                file_info['file_type'],
                file_info['file_size'],
                file_info['last_modified'],
                file_info['file_hash'],
                file_info['is_parsed'],
                file_info['parsed_at']
            )
            self.cursor.execute(query, values)
            self.conn.commit()
            logger.debug(f"已插入文件: {file_info['path']}")
        except Error as e:
            logger.error(f"插入文件失败 {file_info['path']}: {e}")
            self.conn.rollback()
    
    def _update_file(self, file_info):
        """
        更新数据库中的文件信息
        
        Args:
            file_info (dict): 包含文件信息的字典
        """
        try:
            query = """
            UPDATE doc_documents 
            SET file_size = %s, last_modified = %s, file_hash = %s
            WHERE path = %s
            """
            values = (
                file_info['file_size'],
                file_info['last_modified'],
                file_info['file_hash'],
                file_info['path']
            )
            self.cursor.execute(query, values)
            self.conn.commit()
            logger.debug(f"已更新文件: {file_info['path']}")
        except Error as e:
            logger.error(f"更新文件失败 {file_info['path']}: {e}")
            self.conn.rollback()
    
    def scan_files(self):
        """扫描目录下的所有文件并将信息存入数据库"""
        total_files = 0
        processed_files = 0
        
        logger.info(f"开始扫描目录: {self.scan_dir}")
        
        for root, _, files in os.walk(self.scan_dir):
            for file in files:
                total_files += 1
                abs_path = os.path.join(root, file)
                rel_path = self._get_relative_path(abs_path)
                
                try:
                    # 获取文件信息
                    file_stat = os.stat(abs_path)
                    file_size = file_stat.st_size
                    last_modified = datetime.datetime.fromtimestamp(file_stat.st_mtime)
                    file_name = os.path.basename(abs_path)
                    file_type = os.path.splitext(file_name)[1].lower().lstrip('.')
                    file_hash = self._calculate_file_hash(abs_path)
                    
                    # 准备文件信息
                    file_info = {
                        'path': rel_path,
                        'file_name': file_name,
                        'file_type': file_type,
                        'file_size': file_size,
                        'last_modified': last_modified,
                        'file_hash': file_hash,
                        'is_parsed': False,
                        'parsed_at': None
                    }
                    
                    # 如果是增量更新模式，检查文件是否已存在
                    if not self.clear_table and self._file_exists_in_db(rel_path):
                        self._update_file(file_info)
                    else:
                        self._insert_file(file_info)
                    
                    processed_files += 1
                    
                    # 每处理100个文件输出一次进度
                    if processed_files % 100 == 0:
                        logger.info(f"已处理 {processed_files}/{total_files} 个文件")
                        
                except Exception as e:
                    logger.error(f"处理文件失败 {abs_path}: {e}")
        
        logger.info(f"扫描完成，共处理 {processed_files}/{total_files} 个文件")
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("数据库连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='扫描文件并将信息存入数据库')
    parser.add_argument('--no-clear', action='store_true', help='不清空表，使用增量更新模式')
    args = parser.parse_args()
    
    # 扫描目录固定为'DOCS/'
    scan_dir = 'knlgdocs/'
    
    try:
        # 创建文件扫描器实例
        scanner = FileScanner(scan_dir, clear_table=not args.no_clear)
        
        # 扫描文件
        scanner.scan_files()
        
        # 关闭数据库连接
        scanner.close()
        
        logger.info("文件扫描完成")
        return 0
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())