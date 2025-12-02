# FastAPI 文档处理服务 API 使用手册

## 概述

本文档提供 FastAPI 文档处理服务的 API 接口说明，支持完整的文档处理流程：数据源接入 → 文档预处理 → 文档切片 → 文本向量化 → 索引构建 → 向量存储。

## 基础信息

- **服务地址**: `http://localhost:8271`
- **API 文档**: `http://localhost:8271/docs`
- **ReDoc 文档**: `http://localhost:8271/redoc`

## 服务接口汇总表

| 服务名 | 公网端口 | 内部端口 | 接口名 | 功能简述 | URL | 参数说明 |
|--------|----------|----------|--------|----------|-----|----------|
| 文档处理服务 | 8271 | 8271 | POST /batch-process | 批量文档处理 | `http://localhost:8271/batch-process` | `file_paths`: 文件路径列表 |
| 文档处理服务 | 8271 | 8271 | GET /batch-status/{batch_id} | 批任务状态查询 | `http://localhost:8271/batch-status/{batch_id}` | `batch_id`: 批任务ID |
| 文档处理服务 | 8271 | 8271 | GET /health | 健康检查 | `http://localhost:8271/health` | 无参数 |

## 支持的文档格式

### 需要预处理的格式
- `.doc` - Word 97-2003 文档
- `.docx` - Word 文档
- `.pdf` - PDF 文档

### 直接支持的格式
- `.md` / `.markdown` - Markdown 文档
- `.xlsx` / `.xls` - Excel 文档
- `.csv` - CSV 文件
- `.txt` - 纯文本文件

## API 接口

### 1. 批量文档处理接口

**POST** `/batch_process`

批量处理文档文件，支持多个具体文件路径。系统会根据文件格式自动选择处理流程。

#### 请求体
```json
{
  "file_paths": ["string"],  // 文件路径列表，多个文件路径用逗号分隔
  "klg_base_code": "string",  // 知识库编号，每次请求只能指定一个知识库编号
  "timeout": 600  // 超时时间（秒），可选，默认600秒
}
```

- `file_paths` (必需): 文件路径列表，支持多个文件，文件路径之间用逗号分隔
- `klg_base_code` (必需): 知识库编号，用于标识文档所属的知识库，每次请求只能指定一个知识库编号
- `timeout` (可选): 超时时间（秒），默认600秒

#### 响应示例
```json
{
  "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

#### 使用示例（单个文件）
```bash
curl -X POST "http://localhost:8271/batch-process" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": ["e:/documents/example.docx"],
    "klg_base_code": "knowledge_base_001",
    "timeout": 600
  }'
```

#### 使用示例（多个文件）
```bash
curl -X POST "http://localhost:8271/batch-process" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": ["e:/documents/doc1.docx", "e:/documents/doc2.pdf"],
    "klg_base_code": "knowledge_base_002",
    "timeout": 600
  }'
```





### 2. 批任务状态查询接口

**GET** `/batch-status/{batch_id}`

查询特定批处理任务的状态信息。

#### 请求参数
- `batch_id` (路径参数): 批任务ID

#### 响应示例
```json
{
  "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "total_files": 3,
  "success_count": 2,
  "failed_count": 1,
  "create_time": "2025-08-31T15:30:00",
  "update_time": "2025-08-31T15:35:00"
}
```

#### 使用示例
```bash
curl "http://localhost:8271/batch-status/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### 3. 健康检查

**GET** `/health`

检查服务是否正常运行。

#### 响应示例
```json
{
  "status": "healthy",
  "timestamp": 1735622400.123456
}
```

#### 使用示例
```bash
curl "http://localhost:8271/health"
```

## 处理流程说明

### 1. Word/PDF 文档处理流程
1. **文档预处理**: 调用文档解析器将Word/PDF转换为Markdown格式
2. **文档切片**: 对生成的Markdown内容进行文本切片
3. **文本向量化**: 使用BGE-M3模型进行向量化处理
4. **向量存储**: 存储向量化结果到Milvus向量数据库

### 2. MD/Excel/TXT/CSV 文档处理流程
1. **跳过预处理**: 直接读取文件内容
2. **文档切片**: 对原始内容进行文本切片
3. **文本向量化**: 使用BGE-M3模型进行向量化处理
4. **向量存储**: 存储向量化结果到Milvus向量数据库

## 错误处理

### 常见错误代码
- `400 Bad Request`: 请求参数错误，文件不存在或不支持的文件格式
- `404 Not Found`: 任务ID不存在
- `500 Internal Server Error`: 服务器内部错误

### 错误信息格式
错误响应中包含详细的错误描述，便于调试和处理。

## Python 客户端示例

```python
import requests
import time

class DocumentProcessorClient:
    def __init__(self, base_url="http://localhost:8271"):
        self.base_url = base_url
    
    def batch_process(self, file_paths):
        """批量处理文档任务"""
        payload = {
            "file_paths": file_paths
        }
        response = requests.post(f"{self.base_url}/batch_process", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_batch_status(self, batch_id):
        """查询批任务状态"""
        response = requests.get(f"{self.base_url}/batch-status/{batch_id}")
        response.raise_for_status()
        return response.json()
    
    def health_check(self):
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = DocumentProcessorClient()
    
    # 健康检查
    print("服务状态:", client.health_check())
    
    # 提交多个文件处理
    result = client.batch_process([
        "e:/documents/example.docx",
        "e:/documents/doc2.pdf",
        "e:/documents/data.xlsx"
    ])
    print(f"批量任务已提交，ID: {result['batch_id']}")
    
    # 查询批任务状态
    batch_status = client.get_batch_status(result['batch_id'])
    print("批任务状态:", batch_status)
```

## 注意事项

1. **文件路径**: 必须使用绝对路径，确保服务有读取权限
2. **超时时间**: 默认600秒，可配置
3. **资源需求**: 向量化处理需要较多内存和计算资源
4. **模型下载**: 首次运行会自动下载BGE-M3模型（约2.2GB）
5. **输出目录**: 处理结果保存在项目目录的相应子目录中

## 版本信息

- **服务版本**: 1.0.0
- **API 版本**: v1
- **最后更新**: 2025-08-31

---

如有问题，请查看自动生成的API文档或联系开发团队。