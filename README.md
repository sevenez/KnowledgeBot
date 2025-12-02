# KnowledgeBot企业知识库智能问答系统

## 项目概述

KnowledgeBot是一个基于现代技术栈构建的企业知识库智能问答系统，专注于提供高效、准确的文档管理和语义检索服务。系统采用纯后端架构，通过FastAPI提供RESTful API接口，支持前端应用进行结果展示和交互。

## 核心功能

### 文档处理

- **多格式支持**：支持Word、PDF、Excel、TXT、Markdown、CSV等多种文档格式
- **批量处理**：支持大规模文档的批量上传和处理
- **增量更新**：支持文档的增量解析和更新，提高处理效率
- **文档切片**：智能的文档切片策略，保证语义完整性

### 向量检索

- **文本向量化**：基于BGE-M3模型的高效文本向量化
- **向量存储**：使用Milvus向量数据库进行向量存储和检索
- **混合检索**：结合BM25关键词检索和向量语义检索的混合策略
- **RRF融合**：使用Reciprocal Rank Fusion算法融合多种检索结果

### API服务

- **RESTful接口**：提供标准的RESTful API接口
- **批量操作**：支持批量文档处理、删除和状态查询
- **实时状态**：完整的文档处理状态跟踪和查询
- **健康检查**：提供服务健康状态检查接口

## 系统架构

### 整体架构

```
数据源接入 → 文档预处理 → 文档切片 → 文本向量化 → 索引构建 → 向量存储 → 检索服务
```

### 模块划分

- **文档管理模块**：数据源接入、文件监控、批量处理
- **知识库管理模块**：文档预处理、文档切片、文本向量化、索引构建、向量存储
- **检索服务模块**：混合检索、查询增强、结果过滤

### 技术栈

| 类别       | 技术          | 版本        |
| ---------- | ------------- | ----------- |
| 开发语言   | Python        | 3.11.x      |
| Web框架    | FastAPI       | 0.104.x     |
| 文档解析   | MinerU        | 2.3.x       |
| 向量模型   | BGE-M3        | 最新稳定版  |
| 向量数据库 | Milvus        | 2.3.x       |
| 关系数据库 | MySQL         | 8.0.34      |
| 缓存       | Redis         | 7.2.x       |
| 对象存储   | MinIO         | 2024-05-07+ |
| 搜索引擎   | Elasticsearch | 8.11.x      |
| 任务调度   | APScheduler   | 3.10.x      |

## 安装部署

### 环境要求

- Python 3.11.x
- MySQL 8.0.34
- Redis 7.2.x
- Milvus 2.3.x
- MinIO（可选，用于对象存储）

### 安装步骤

1. **克隆项目**

   ```bash
   git clone <repository-url>
   cd KnowledgeBot企业知识库智能问答系统
   ```
2. **安装依赖**

   ```bash
   pip install -r source/FastAPI_Processor/requirements.txt
   ```
3. **配置数据库**

   编辑数据库配置文件，确保MySQL连接信息正确。
4. **启动服务**

   使用提供的启动脚本启动服务：

   ```bash
   python source/FastAPI_Processor/run_server.py
   ```

   或使用自定义参数启动：

   ```bash
   python source/FastAPI_Processor/run_server.py --host 0.0.0.0 --port 8271 --reload --workers 4
   ```

## 服务配置

### 启动参数

| 参数      | 类型   | 默认值  | 描述                   |
| --------- | ------ | ------- | ---------------------- |
| --host    | string | 0.0.0.0 | 服务监听地址           |
| --port    | int    | 8271    | 服务监听端口           |
| --reload  | bool   | False   | 启用热重载（开发模式） |
| --workers | int    | 1       | 工作进程数量           |

### 服务地址

- **服务地址**：http://localhost:8271
- **API文档**：http://localhost:8271/docs
- **ReDoc文档**：http://localhost:8271/redoc

## API接口

### 健康检查

```
GET /health
```

返回服务健康状态。

### 文档解析

```
POST /parse-document
```

单独的文档解析接口，只进行文档预处理，不包含向量化等后续步骤。

**请求体**：

```json
{
  "file_path": "path/to/document.pdf",
  "timeout": 300
}
```

### 批量处理

```
POST /batch-process
```

批量处理文档，包括预处理、切片、向量化和存储等完整流程。

**请求体**：

```json
{
  "file_paths": [
    "path/to/document1.pdf",
    "path/to/document2.docx"
  ],
  "klg_base_code": "knowledge_base_1",
  "timeout": 600
}
```

### 批量任务状态

```
GET /batch-status/{batch_id}
```

获取批量处理任务的状态和进度。

### 文档删除

```
DELETE /documents
```

批量删除文档及相关数据，包括向量库中的记录和关联的预处理文件。

**请求体**：

```json
{
  "file_paths": [
    "path/to/document1.pdf",
    "path/to/document2.docx"
  ],
  "klg_base_code": "knowledge_base_1"
}
```

## 文档处理状态

系统实现了完整的文档处理状态跟踪机制：

| 状态码 | 描述                                  |
| ------ | ------------------------------------- |
| 0      | 未解析 - 文档已识别但尚未开始处理     |
| 1      | 已解析 - 文档已完成解析和预处理       |
| 2      | 已向量化 - 文档已完成向量化和索引构建 |

## 使用示例

### Python客户端示例

```python
import requests
import time

# 批量处理文档
batch_request = {
    "file_paths": [
        "documents/report1.pdf",
        "documents/manual.docx"
    ],
    "klg_base_code": "kb_001",
    "timeout": 600
}

response = requests.post(
    "http://localhost:8271/batch-process",
    json=batch_request
)

# 查询处理状态
batch_id = response.json()["batch_id"]
while True:
    status_response = requests.get(
        f"http://localhost:8271/batch-status/{batch_id}"
    )
    status_data = status_response.json()
  
    if status_data['overall_status'] in ['completed', 'failed']:
        break
  
    time.sleep(10)
```

### cURL示例

```bash
# 批量处理
curl -X POST "http://localhost:8271/batch-process" \
  -H "Content-Type: application/json" \
  -d '{"file_paths": ["doc1.pdf", "doc2.docx"], "klg_base_code": "kb_001", "timeout": 600}'

# 查询状态
curl -X GET "http://localhost:8271/batch-status/{batch_id}"

# 删除文档
curl -X DELETE "http://localhost:8271/documents" \
  -H "Content-Type: application/json" \
  -d '{"file_paths": ["doc1.pdf", "doc2.docx"], "klg_base_code": "kb_001"}'
```

## 性能优化

### GPU加速

- 模型加载优先使用GPU内存
- 批量编码充分利用GPU并行计算
- 无GPU环境下自动降级到CPU处理

### 处理性能

- 单次处理文件数量建议不超过50个
- 单个文件大小限制为15MB
- 系统自动并发处理多个文件

### 内存管理

- 使用Redis缓存热点数据
- 实现高效的内存使用策略
- 支持大规模文档处理时的内存优化

## 安全与合规

### 安全措施

- API Key/Bearer Token认证
- 敏感信息通过环境变量管理
- 仅允许访问授权目录
- 支持配置文件和传输数据加密

### 数据合规

- 对含敏感信息的文档进行标注或跳过处理
- 定义数据保留周期和清理策略
- 记录所有操作日志用于审计

## 监控与维护

### 关键监控指标

- 任务提交数、成功率、平均完成时长
- GPU利用率、系统资源使用情况
- 数据库连接状态、缓存命中率

### 常见错误处理

1. **文件不存在**：检查文件路径是否正确
2. **不支持的格式**：确认文件格式在支持列表中
3. **数据库连接失败**：检查MySQL配置和连接
4. **向量化失败**：检查GPU内存和模型加载
5. **存储失败**：检查磁盘空间和权限

## 后续规划

### 近期优化

- 进一步优化向量化计算性能
- 扩展更多文档格式支持
- 增强查询理解和结果排序

### 中长期规划

- 支持多语言文档处理
- 集成知识图谱增强语义理解
- 实现完整的自动化运维体系

## 许可证

[MIT License]
