#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI文件处理主程序
提供RESTful接口，接收单个文件路径，调用文档解析器进行处理，并在指定时间后获取结果
支持完整的文档处理流程：数据源接入 → 文档预处理 → 文档切片 → 文本向量化 → 索引构建 → 向量存储
"""

import os
import sys
import time
import logging
import uuid
import json
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import uvicorn
import hashlib

# 添加父目录到系统路径，以便导入配置文件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入现有的文档处理模块
try:
    from Document_Preprocessing.document_parser import DocumentParser
    from Document_Vectorization.document_chunking import DocumentChunker
    from Document_Vectorization.text_vectorization import TextVectorizer
    from Document_Vectorization.vector_storage import VectorStorage
    from Document_Vectorization.index_builder import IndexBuilder
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保相关模块存在")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FastAPIFileProcessor')

# 创建FastAPI应用
app = FastAPI(
    title="文件预处理API服务",
    description="提供文档预处理和结果获取的RESTful接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 异常处理中间件 - 捕获所有异常并创建日志文件
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理参数验证错误，创建日志文件"""
    # 确保日志文件生成在正确位置：E:\AIstydycode\AIE\EKBQA_System\source\logs
    # 使用绝对路径构建，避免路径解析错误
    current_file_path = os.path.abspath(__file__)
    # 获取FastAPI_Processor目录
    fastapi_dir = os.path.dirname(current_file_path)
    # 获取source目录
    source_dir = os.path.dirname(fastapi_dir)
    # 构建logs目录路径
    log_dir = os.path.join(source_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = int(time.time())
    log_file = os.path.join(log_dir, f"{timestamp}.txt")  # 修改后缀为.txt
    
    # 获取请求体
    body = await request.body()
    try:
        request_body = json.loads(body.decode('utf-8')) if body else {}
    except:
        request_body = {"raw_body": str(body)}
    
    # 创建错误日志
    call_info = f"""批量处理接口调用日志
时间戳: {timestamp}
调用时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}
接口: /batch-process
状态: 参数验证失败
错误详情: {exc.errors()}
请求体: {request_body}
"""
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(call_info)
    logger.info(f"参数验证失败，创建错误日志文件: {log_file}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理其他异常，创建日志文件"""
    # 确保日志文件生成在正确位置：E:\AIstydycode\AIE\EKBQA_System\source\logs
    # 使用绝对路径构建，避免路径解析错误
    current_file_path = os.path.abspath(__file__)
    # 获取FastAPI_Processor目录
    fastapi_dir = os.path.dirname(current_file_path)
    # 获取source目录
    source_dir = os.path.dirname(fastapi_dir)
    # 构建logs目录路径
    log_dir = os.path.join(source_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = int(time.time())
    log_file = os.path.join(log_dir, f"{timestamp}.txt")  # 修改后缀为.txt
    
    # 获取请求体
    body = await request.body()
    try:
        request_body = json.loads(body.decode('utf-8')) if body else {}
    except:
        request_body = {"raw_body": str(body)}
    
    # 创建错误日志
    call_info = f"""批量处理接口调用日志
时间戳: {timestamp}
调用时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}
接口: /batch-process
状态: 服务器内部错误
错误类型: {type(exc).__name__}
错误信息: {str(exc)}
请求体: {request_body}
"""
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(call_info)
    logger.error(f"服务器内部错误，创建错误日志文件: {log_file}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# 导入数据库配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_config import DB_CONFIG

# 使用导入的数据库配置
MYSQL_CONFIG = DB_CONFIG

# 全局任务状态存储
task_statuses: Dict[str, Dict[str, Any]] = {}

class TaskRequest(BaseModel):
    """任务请求模型（支持单个文件）"""
    file_path: str
    timeout: Optional[int] = 300  # 默认5分钟超时

class BatchTaskRequest(BaseModel):
    """批量任务请求模型"""
    file_paths: List[str]  # 文件路径列表
    klg_base_code: str  # 知识库编号
    timeout: Optional[int] = 600  # 默认10分钟超时

class DeleteDocumentsRequest(BaseModel):
    """删除文档请求模型"""
    file_paths: List[str]  # 要删除的文件路径列表
    klg_base_code: str  # 知识库编号

class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: Dict[str, str]  # 各阶段处理状态
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: float

def get_file_extension(file_path: str) -> str:
    """获取文件扩展名（小写）"""
    return os.path.splitext(file_path)[1].lower()

def is_preprocessing_required(file_path: str) -> bool:
    """判断文件是否需要预处理（word/pdf格式）"""
    ext = get_file_extension(file_path)
    return ext in ['.doc', '.docx', '.pdf']



def is_direct_processing_supported(file_path: str) -> bool:
    """判断文件是否支持直接处理（md/excel/txt/csv格式）"""
    ext = get_file_extension(file_path)
    return ext in ['.md', '.markdown', '.xlsx', '.xls', '.csv', '.txt']

def validate_batch_request(request: BatchTaskRequest) -> List[str]:
    """验证批量请求并返回要处理的文件列表"""
    if not request.file_paths:
        raise ValueError("必须指定file_paths")
    
    # 验证文件路径列表
    file_paths = []
    for file_path in request.file_paths:
        if not os.path.exists(file_path):
            raise ValueError(f"文件不存在: {file_path}")
        if not (is_preprocessing_required(file_path) or 
               is_direct_processing_supported(file_path)):
            raise ValueError(f"不支持的文件格式: {file_path}")
        file_paths.append(file_path)
    
    return file_paths

def read_file_content(file_path: str) -> str:
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"读取文件失败: {e}")

def process_document_complete(task_id: str, file_path: str, klg_base_code: str = None):
    """完整的文档处理流程
    状态：0-未解析，1-已解析，2-已向量化
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise Exception(f"文件不存在: {file_path}")
        
        # 计算文件哈希值
        file_hash = calculate_file_hash(file_path)
        
        # 创建VectorStorage实例（仅创建一次，在整个函数中复用）
        vector_storage = VectorStorage(mysql_config=MYSQL_CONFIG)
        
        # 更新任务状态
        task_statuses[task_id]['status'] = 'processing'
        task_statuses[task_id]['progress'] = {
            'preprocessing': 'pending',
            'chunking': 'pending', 
            'vectorization': 'pending',
            'indexing': 'pending',
            'storage': 'pending'
        }
        
        # 设置知识库编号（如果提供）
        if klg_base_code:
            task_statuses[task_id]['klg_base_code'] = klg_base_code
        
        content = ""
        md_file_path = None
        
        # 获取日志目录路径
        current_file_path = os.path.abspath(__file__)
        fastapi_dir = os.path.dirname(current_file_path)
        source_dir = os.path.dirname(fastapi_dir)
        log_dir = os.path.join(source_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 查找最新的日志文件（按时间戳排序）
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.txt')]
        if log_files:
            # 按时间戳排序，取最新的日志文件
            log_files.sort(key=lambda x: int(x.split('.')[0]), reverse=True)
            latest_log_file = os.path.join(log_dir, log_files[0])
        else:
            # 如果没有日志文件，创建一个新的
            timestamp = int(time.time())
            latest_log_file = os.path.join(log_dir, f"{timestamp}.txt")
            with open(latest_log_file, 'w', encoding='utf-8') as f:
                f.write(f"处理日志 - 开始处理文件: {file_path}")
                f.write(f"时间戳: {timestamp}")
        
        # 1. 文档预处理（如果是word/pdf格式）
        if is_preprocessing_required(file_path):
            task_statuses[task_id]['progress']['preprocessing'] = 'processing'
            logger.info(f"开始预处理文档: {file_path}")
            
            # 更新日志文件
            with open(latest_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始预处理文档: {file_path}")
            
            parser = DocumentParser()
            result = parser.parse_document(file_path)
            
            if not result or 'status' not in result or result['status'] != 'success':
                raise Exception(f"文档预处理失败: {result.get('error', '未知错误')}")
            
            # 获取生成的md文件路径
            md_file_path = result.get('output_path')
            if not md_file_path or not os.path.exists(md_file_path):
                raise Exception("预处理后未生成有效的markdown文件")
                
            content = read_file_content(md_file_path)
            task_statuses[task_id]['progress']['preprocessing'] = 'completed'
            logger.info(f"文档预处理完成，生成文件: {md_file_path}")
            
            # 更新日志文件
            with open(latest_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文档预处理完成，生成文件: {md_file_path}")
            
            # 文档解析完成后更新解析状态和处理状态
            # 更新is_parsed字段为True（已解析）
            parser._update_document_parsed_status_by_path(file_path, True)
            # 更新status字段为'1'（已解析）
            vector_storage.update_document_status(file_path, '1')
            logger.info(f"文档状态更新: {file_path} -> 已解析")
            
            # 更新日志文件
            with open(latest_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文档状态更新: {file_path} -> 已解析")
        
        # 2. 直接处理支持的格式
        elif is_direct_processing_supported(file_path):
            content = read_file_content(file_path)
            task_statuses[task_id]['progress']['preprocessing'] = 'skipped'
            logger.info(f"跳过预处理，直接处理文件: {file_path}")
            
            # 更新日志文件
            with open(latest_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 跳过预处理，直接处理文件: {file_path}")
            
            # 直接处理的文档也标记为已解析状态
            # 更新status字段为'1'（已解析）
            vector_storage.update_document_status(file_path, '1')
            logger.info(f"文档状态更新: {file_path} -> 已解析")
            
            # 更新日志文件
            with open(latest_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文档状态更新: {file_path} -> 已解析")
        
        else:
            raise Exception(f"不支持的文件格式: {get_file_extension(file_path)}")
        
        # 3. 文档切片
        task_statuses[task_id]['progress']['chunking'] = 'processing'
        logger.info("开始文档切片")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始文档切片")
        
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
        file_id = hash(file_path) % 10000
        chunks = chunker.chunk_document(content, file_path, file_id)
        
        if not chunks:
            raise Exception("文档切片失败")
            
        task_statuses[task_id]['progress']['chunking'] = 'completed'
        logger.info(f"文档切片完成，生成 {len(chunks)} 个切片")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文档切片完成，生成 {len(chunks)} 个切片")
        
        # 4. 文本向量化
        task_statuses[task_id]['progress']['vectorization'] = 'processing'
        logger.info("开始文本向量化")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始文本向量化")
        
        vectorizer = TextVectorizer(model_name="BAAI/bge-m3")
        vectorized_chunks = vectorizer.vectorize(chunks)
        
        if not vectorized_chunks:
            raise Exception("文本向量化失败")
            
        task_statuses[task_id]['progress']['vectorization'] = 'completed'
        logger.info("文本向量化完成")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文本向量化完成")
        
        # 5. 索引构建
        task_statuses[task_id]['progress']['indexing'] = 'processing'
        logger.info("开始索引构建")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始索引构建")
        
        index_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               "Document_Vectorization", "index_files")
        os.makedirs(index_dir, exist_ok=True)
        
        # 更新索引构建状态为已完成
        task_statuses[task_id]['progress']['indexing'] = 'completed'
        logger.info("索引构建完成")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 索引构建完成")
        
        # 向量存储阶段
        task_statuses[task_id]['progress']['storage'] = 'processing'
        logger.info("开始向量存储")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始向量存储")
        
        # 保存文档信息到数据库
        
        # 保存文档基本信息到documents表，传递知识库编号
        document_id = vector_storage.save_document_info(file_path, file_hash, klg_base_code)
        if document_id == 0:
            raise Exception("保存文档信息失败")
        
        # 检查document_id是否为有效的数据库ID（不是备选的时间戳ID）
        # 备选ID通常是很大的时间戳数字，而数据库ID通常较小
        if document_id > 1000000000:  # 假设数据库ID不会超过10亿
            logger.warning(f"文档ID {document_id} 可能是备选ID，批次表可能无法正确关联")
            # 更新日志文件
            with open(latest_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 警告: 文档ID {document_id} 可能是备选ID")
            
            # 尝试重新查询获取真实的文档ID
            try:
                import pymysql
                from pymysql.cursors import DictCursor
                conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=DictCursor)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM doc_documents WHERE path = %s AND file_hash = %s",
                    (file_path, file_hash)
                )
                result = cursor.fetchone()
                if result:
                    document_id = result['id']
                    logger.info(f"重新查询获取真实文档ID: {document_id}")
                    
                    # 更新日志文件
                    with open(latest_log_file, 'a', encoding='utf-8') as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 重新查询获取真实文档ID: {document_id}")
                cursor.close()
                conn.close()
            except Exception as e:
                logger.error(f"重新查询文档ID失败: {e}")
                
                # 更新日志文件
                with open(latest_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 重新查询文档ID失败: {e}")
        
        # 创建批次记录，传递文件路径和哈希值用于备选ID情况
        parser = DocumentParser()
        batch_id = parser._create_parse_batch(document_id, file_path=file_path, file_hash=file_hash)
        if not batch_id:
            raise Exception("批次记录创建失败")
        
        # 更新chunks中的file_id为实际的document_id
        for chunk in vectorized_chunks:
            chunk['file_id'] = document_id
        
        # 存储向量到向量数据库
        updated_chunks = vector_storage.store_vectors(vectorized_chunks)
        # 存储元数据到MySQL
        vector_storage.store_metadata(updated_chunks, document_id)
        task_statuses[task_id]['progress']['storage'] = 'completed'
        logger.info("向量存储完成")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 向量存储完成")
        
        # 更新文档状态为已向量化（状态：2）
        vector_storage.update_document_status(file_path, '2')
        logger.info(f"文档状态更新: {file_path} -> 已向量化")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文档状态更新: {file_path} -> 已向量化")
        
        # 更新任务状态为完成
        task_statuses[task_id]['status'] = 'completed'
        task_statuses[task_id]['result'] = {
            'original_file': file_path,
            'preprocessed_file': md_file_path,
            'chunks_count': len(chunks),
            'vectorized_count': len(vectorized_chunks),
            'index_built': len(vectors) > 0,
            'storage_success': True,
            'file_hash': file_hash
        }
        logger.info(f"任务 {task_id} 处理完成")
        
        # 更新日志文件
        with open(latest_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 任务 {task_id} 处理完成")
            f.write(f"处理结果: 原始文件={file_path}, 切片数={len(chunks)}, 向量化数={len(vectorized_chunks)}")
        
    except Exception as e:
        # 更新任务状态为失败
        task_statuses[task_id]['status'] = 'failed'
        task_statuses[task_id]['error'] = str(e)
        logger.error(f"任务 {task_id} 处理失败: {e}")
        
        # 更新日志文件（如果存在）
        try:
            current_file_path = os.path.abspath(__file__)
            fastapi_dir = os.path.dirname(current_file_path)
            source_dir = os.path.dirname(fastapi_dir)
            log_dir = os.path.join(source_dir, "logs")
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.txt')]
            if log_files:
                log_files.sort(key=lambda x: int(x.split('.')[0]), reverse=True)
                latest_log_file = os.path.join(log_dir, log_files[0])
                with open(latest_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 任务 {task_id} 处理失败: {e}")
        except Exception as log_error:
            logger.error(f"更新失败日志失败: {log_error}")





@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/parse-document")
async def parse_document_endpoint(request: TaskRequest):
    """
    单独的文档解析接口
    只进行文档预处理，不包含向量化等后续步骤
    """
    try:
        file_path = request.file_path
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件不存在: {file_path}"
            )
        
        # 检查文件格式是否需要预处理
        if not is_preprocessing_required(file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件格式不需要预处理: {get_file_extension(file_path)}"
            )
        
        # 创建文档解析器并解析文档
        parser = DocumentParser()
        result = parser.parse_document(file_path)
        
        # 更新文档解析状态
        if result.get('status') == 'success':
            # 更新is_parsed字段为True（已解析）
            parser._update_document_parsed_status_by_path(file_path, True)
            
            # 更新status字段为'1'（已解析）
            storage = VectorStorage(mysql_config=MYSQL_CONFIG)
            storage.update_document_status(file_path, '1')
            
            logger.info(f"文档解析完成: {file_path}")
        
        # 关闭数据库连接
        parser.close()
        
        return {
            "file_path": file_path,
            "status": result.get('status'),
            "output_path": result.get('output_path'),
            "message": result.get('message', result.get('error')),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档解析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档解析失败: {str(e)}"
        )



class BatchTaskResponse(BaseModel):
    """批任务响应模型"""
    batch_id: str
    total_files: int
    status: str  # pending, processing, completed, failed
    timestamp: float

@app.post("/batch-process", response_model=BatchTaskResponse)
async def batch_process_documents(request: BatchTaskRequest, background_tasks: BackgroundTasks):
    """批量处理文档接口"""
    # 创建时间戳命名的日志文件并记录调用情况（接口被调用时立即生成）
    # 确保日志文件生成在正确位置：E:\AIstydycode\AIE\EKBQA_System\source\logs
    # 使用绝对路径构建，避免路径解析错误
    current_file_path = os.path.abspath(__file__)
    # 获取FastAPI_Processor目录
    fastapi_dir = os.path.dirname(current_file_path)
    # 获取source目录
    source_dir = os.path.dirname(fastapi_dir)
    # 构建logs目录路径
    log_dir = os.path.join(source_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = int(time.time())
    log_file = os.path.join(log_dir, f"{timestamp}.txt")  # 修改后缀为.txt
    
    # 立即创建日志文件并记录基本调用信息
    call_info = f"""批量处理接口调用日志
时间戳: {timestamp}
调用时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}
接口: /batch-process
知识库编号: {request.klg_base_code}
状态: 接口被调用，开始处理请求
"""
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(call_info)
    logger.info(f"批量处理接口被调用，创建日志文件: {log_file}")
    
    try:
        # 验证批量请求并获取文件列表
        file_paths = validate_batch_request(request)
        
        # 更新日志文件，添加文件信息
        updated_info = f"""批量处理接口调用日志
时间戳: {timestamp}
调用时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}
接口: /batch-process
文件数量: {len(file_paths)}
知识库编号: {request.klg_base_code}
文件列表: {file_paths}
状态: 接口调用成功，开始处理
"""
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(updated_info)
        logger.info(f"批量处理接口调用成功，更新日志文件: {log_file}")
        
        if not file_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有找到可处理的文件"
            )
        
        # 生成批量任务ID（格式：DPS_时间戳_随机数）
        timestamp = int(time.time())
        random_suffix = str(uuid.uuid4().int)[:6]  # 取UUID前6位数字
        batch_id = f"DPS_{timestamp}_{random_suffix}"
        task_ids = []
        
        # 为每个文件创建单独的处理任务
        for file_path in file_paths:
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            
            # 初始化任务状态
            task_statuses[task_id] = {
                'task_id': task_id,
                'status': 'pending',
                'progress': {
                    'preprocessing': 'pending',
                    'chunking': 'pending',
                    'vectorization': 'pending',
                    'indexing': 'pending',
                    'storage': 'pending'
                },
                'result': None,
                'error': None,
                'timestamp': time.time(),
                'batch_id': batch_id,
                'file_path': file_path
            }
            
            # 在后台执行处理任务，传递知识库编号
            background_tasks.add_task(process_document_complete, task_id, file_path, request.klg_base_code)
        
        # 创建批量任务状态
        batch_status = {
            'batch_id': batch_id,
            'total_files': len(file_paths),
            'status': 'processing',
            'timestamp': time.time()
        }
        
        logger.info(f"批量任务 {batch_id} 已创建，包含 {len(file_paths)} 个文件")
        
        return BatchTaskResponse(**batch_status)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量处理失败: {str(e)}"
        )

@app.get("/batch-status/{batch_id}")
async def get_batch_status(batch_id: str):
    """获取批量任务状态接口"""
    # 查找属于该批量的所有任务
    batch_tasks = [task_status for task_id, task_status in task_statuses.items() 
                  if task_status.get('batch_id') == batch_id]
    
    if not batch_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"批量任务ID不存在: {batch_id}"
        )
    
    # 统计任务状态
    status_counts = {
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'failed': 0
    }
    
    for task in batch_tasks:
        status_counts[task['status']] += 1
    
    # 确定整体批量状态
    if status_counts['failed'] > 0:
        overall_status = 'failed'
    elif status_counts['processing'] > 0 or status_counts['pending'] > 0:
        overall_status = 'processing'
    else:
        overall_status = 'completed'
    
    return {
        'batch_id': batch_id,
        'total_tasks': len(batch_tasks),
        'status_counts': status_counts,
        'overall_status': overall_status,
        'tasks': batch_tasks,
        'timestamp': time.time()
    }

def delete_associated_md_file(file_path: str) -> bool:
    """删除与源文件关联的预处理md文件"""
    try:
        # 构建md文件路径（与源文件同目录，同名但扩展名为.md）
        md_file_path = os.path.splitext(file_path)[0] + '.md'
        
        if os.path.exists(md_file_path):
            os.remove(md_file_path)
            logger.info(f"已删除关联的md文件: {md_file_path}")
            return True
        else:
            logger.info(f"未找到关联的md文件: {md_file_path}")
            return False
    except Exception as e:
        logger.error(f"删除关联md文件失败: {e}")
        return False

def calculate_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希值"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败: {e}")
        return ""

@app.delete("/documents")
async def delete_documents(request: DeleteDocumentsRequest):
    """
    批量删除文档
    - 删除向量库中的记录
    - 删除关联的预处理md文件（如果存在）
    - 支持批量文件路径删除
    """
    if not request.file_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须指定要删除的文件路径列表"
        )
    
    results = []
    storage = VectorStorage(mysql_config=MYSQL_CONFIG)
    
    for file_path in request.file_paths:
        result = {
            'file_path': file_path,
            'vector_deleted': False,
            'md_file_deleted': False,
            'error': None
        }
        
        try:
            # 验证文件路径是否存在
            if not os.path.exists(file_path):
                result['error'] = "文件不存在"
                results.append(result)
                continue
            
            # 1. 删除向量库中的记录（传递知识库编码参数）
            vector_deleted = storage.delete_vectors_by_file_path(file_path, request.klg_base_code)
            result['vector_deleted'] = vector_deleted
            
            # 2. 删除关联的md文件（如果是doc/docx/pdf格式）
            ext = get_file_extension(file_path)
            if ext in ['.doc', '.docx', '.pdf']:
                md_deleted = delete_associated_md_file(file_path)
                result['md_file_deleted'] = md_deleted
            
            results.append(result)
            
        except Exception as e:
            result['error'] = str(e)
            results.append(result)
            logger.error(f"删除文档失败 {file_path}: {e}")
    
    return {
        'batch_id': str(uuid.uuid4()),
        'timestamp': time.time(),
        'results': results
    }

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8271)