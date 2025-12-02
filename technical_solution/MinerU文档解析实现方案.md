# MinerU文档解析实现方案

## 1. 概述

本文档详细描述使用MinerU进行文档解析的实现方案，包括自动增量解析、定时检索和数据库设计等核心功能。MinerU是一个强大的文档解析服务，能够将Word、PDF等格式的文档转换为结构化的Markdown格式，便于后续处理和分析。

## 2. 技术架构

### 2.1 整体流程

```
接口触发 → 文件夹扫描 → 文档上传 → MinerU解析调用 → batch_id保存 → 1分钟后获取结果 → Markdown保存 → 定时检索未成功任务
```

### 2.2 技术选型

- **文档解析引擎**: MinerU 2.3.x
- **开发语言**: Python 3.11.x
- **Web框架**: FastAPI 0.103.x
- **数据库**: MySQL 8.0.34
- **对象存储**: MinIO (2024-05-07及以上稳定版)
- **任务调度**: APScheduler 3.10.x

## 3. 核心功能设计

### 3.1 自动增量解析功能

**功能描述**：
- 接口被调用后，自动扫描指定文件夹内的PDF和Word文件
- 检测新增和修改的文件，避免重复处理
- 通过云API提交在线解析任务
- 获取并保存batch_id到结构化数据库

**处理流程**：
1. 接口触发 → 扫描文件夹
2. 文件变更检测 → 识别新增/修改文件
3. 文件上传到可访问URL → 调用MinerU API
4. 获取batch_id → 保存到数据库
5. 创建定时获取任务 → 1分钟后执行
6. 获取解析结果 → 下载ZIP文件
7. 解压并提取Markdown → 保存到文件夹
8. 更新数据库状态 → 记录完成时间

### 3.2 定时检索机制

**功能描述**：
- 1分钟后自动获取解析结果
- 对于未成功获取的任务，进行定时重试
- 支持指数退避重试策略
- 记录详细的执行日志

**重试策略**：
- 初始延迟：1分钟
- 重试间隔：2^n分钟（最大60分钟）
- 最大重试次数：5次
- 失败后标记为永久失败

## 4. 核心模块设计

### 4.1 MinerU解析调用模块

**功能职责**：
- 文件上传到可访问URL
- 调用MinerU云API提交解析任务
- 获取并保存batch_id到数据库
- 配置解析参数（公式识别、表格识别等）

**主要接口**：
- `submit_document()`: 提交文档解析任务
- `upload_file_to_url()`: 上传文件到可访问地址
- `save_batch_to_db()`: 保存批次信息到数据库

### 4.2 MinerU结果获取模块

**功能职责**：
- 根据batch_id获取解析结果
- 下载并解压结果ZIP文件
- 提取Markdown文件和图片资源
- 保存到指定文件夹并更新数据库状态

**主要接口**：
- `get_parse_result()`: 获取解析结果
- `download_and_extract_result()`: 下载并解压结果
- `update_batch_status()`: 更新批次状态

### 4.3 FastAPI接口服务

**功能职责**：
- 提供RESTful API接口
- 触发文件夹增量解析
- 管理后台任务调度
- 提供解析状态查询

**主要端点**：
- `POST /api/parse-folder`: 解析文件夹
- `GET /api/parse-status/{batch_id}`: 查询解析状态
- `GET /api/batch-list`: 获取批次列表

### 4.4 定时任务调度器

**功能职责**：
- 定时检查待获取的批次
- 实现重试机制和指数退避
- 处理获取失败的情况
- 记录详细的执行日志

**调度策略**：
- 每分钟检查一次待处理任务
- 指数退避重试（2^n分钟，最大60分钟）
- 最大重试5次后标记为失败

## 5. 文件夹监控与增量处理

### 5.1 文件变更检测

**检测机制**：
- 维护文件元数据记录（路径、大小、修改时间、哈希值、解析状态）
- 定期扫描文件夹，对比文件变更
- 支持新增、修改、删除文件的检测
- 检查文档表中的`is_parsed`字段，确定是否需要解析

**增量策略**：
- 新增文件：检查是否已解析，未解析则完整解析并添加到系统，设置`is_parsed=true`
- 修改文件：检查修改时间是否晚于`parsed_at`，若是则重新解析并更新记录
- 删除文件：从系统中移除相关记录

### 5.2 批量处理机制

**处理策略**：
- 设置批处理阈值，避免单次处理过多文件
- 实现优先级队列，优先处理重要文档
- 支持并发处理，提高处理效率

## 6. 自动增量解析与定时检索机制

### 6.1 功能描述

系统提供完整的自动化文档解析流程：

1. **接口触发**：通过RESTful API触发解析任务
2. **文件夹扫描**：自动扫描指定文件夹内的PDF和Word文件
3. **增量检测**：识别新增和修改的文件，检查文档表中的`is_parsed`字段，避免重复处理已解析文件
4. **云API提交**：将未解析的文件上传并提交给MinerU进行在线解析
5. **batch_id管理**：获取并保存batch_id到结构化数据库
6. **定时获取**：1分钟后自动获取解析结果
7. **结果保存**：下载解析结果并保存为Markdown格式到文件夹
8. **状态跟踪**：更新文档表中的`is_parsed`和`parsed_at`字段，记录处理状态和时间信息

### 6.2 核心流程

```
API调用 → 扫描文件夹 → 检测文件变更 → 上传文件 → 调用MinerU API → 
保存batch_id → 创建定时任务 → 1分钟后获取结果 → 保存Markdown → 更新状态
```

### 6.3 定时检索机制

- **初始检索**：提交任务1分钟后进行首次结果获取
- **重试机制**：对于未成功获取的任务，按指数退避策略重试
- **状态管理**：详细记录每次检索尝试的结果和错误信息
- **自动清理**：定期清理过期的临时文件和失败任务

## 7. 数据库表结构设计

### 7.1 文档表（documents）

记录所有待处理文档的基本信息：

```sql
CREATE TABLE `documents` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `path` VARCHAR(512) NOT NULL COMMENT '文件完整路径',
  `name` VARCHAR(256) NOT NULL COMMENT '文件名',
  `extension` VARCHAR(8) NOT NULL COMMENT '文件扩展名',
  `size` BIGINT NOT NULL COMMENT '文件大小(字节)',
  `modified_time` DATETIME NOT NULL COMMENT '文件修改时间',
  `file_hash` VARCHAR(64) DEFAULT NULL COMMENT '文件内容哈希值',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  `status` ENUM('active','deleted') NOT NULL DEFAULT 'active' COMMENT '文件状态',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_path` (`path`),
  KEY `idx_name` (`name`),
  KEY `idx_modified_time` (`modified_time`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文档基本信息表';
```

### 7.2 解析批次表（parse_batches）

存储MinerU返回的batch_id和解析配置：

```sql
CREATE TABLE `parse_batches` (
  `batch_id` VARCHAR(64) NOT NULL COMMENT 'MinerU返回的批次ID',
  `document_id` BIGINT NOT NULL COMMENT '关联文档ID',
  `provider` VARCHAR(64) NOT NULL DEFAULT 'mineru' COMMENT '解析服务提供商',
  `enable_formula` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用公式识别',
  `enable_table` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用表格识别',
  `file_url` VARCHAR(512) DEFAULT NULL COMMENT '上传后的文件访问URL',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '批次创建时间',
  `retrieved_at` DATETIME NULL COMMENT '结果获取成功时间',
  `markdown_path` VARCHAR(512) NULL COMMENT '保存的Markdown文件路径',
  `images_path` VARCHAR(512) NULL COMMENT '保存的图片文件夹路径',
  `status` ENUM('submitted','retrieved','completed','failed') NOT NULL DEFAULT 'submitted' COMMENT '批次状态',
  `error_message` TEXT NULL COMMENT '错误信息',
  PRIMARY KEY (`batch_id`),
  KEY `idx_document` (`document_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  FOREIGN KEY (`document_id`) REFERENCES `documents`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='解析批次信息表';
```

### 7.3 批次检索任务表（batch_retrieval_jobs）

管理定时检索任务的调度信息：

```sql
CREATE TABLE `batch_retrieval_jobs` (
  `job_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `batch_id` VARCHAR(64) NOT NULL COMMENT '关联批次ID',
  `next_run` DATETIME NOT NULL COMMENT '下次执行时间',
  `attempt` INT NOT NULL DEFAULT 0 COMMENT '当前尝试次数',
  `max_attempts` INT NOT NULL DEFAULT 5 COMMENT '最大尝试次数',
  `retry_interval` INT NOT NULL DEFAULT 60 COMMENT '重试间隔(秒)',
  `status` ENUM('scheduled','in_progress','completed','failed') NOT NULL DEFAULT 'scheduled' COMMENT '任务状态',
  `last_error` TEXT NULL COMMENT '最后一次错误信息',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '任务创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '任务更新时间',
  PRIMARY KEY (`job_id`),
  KEY `idx_batch` (`batch_id`),
  KEY `idx_next_run` (`next_run`),
  KEY `idx_status` (`status`),
  FOREIGN KEY (`batch_id`) REFERENCES `parse_batches`(`batch_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='批次检索任务调度表';
```

### 7.4 检索尝试记录表（retrieval_attempts）

记录每次检索尝试的详细信息：

```sql
CREATE TABLE `retrieval_attempts` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `batch_id` VARCHAR(64) NOT NULL COMMENT '关联批次ID',
  `attempt_no` INT NOT NULL COMMENT '尝试次数',
  `attempted_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '尝试时间',
  `success` BOOLEAN NOT NULL COMMENT '是否成功',
  `response_code` INT NULL COMMENT 'API响应状态码',
  `response_message` TEXT NULL COMMENT 'API响应消息',
  `execution_time` INT NULL COMMENT '执行耗时(毫秒)',
  `error_details` TEXT NULL COMMENT '详细错误信息',
  PRIMARY KEY (`id`),
  KEY `idx_batch` (`batch_id`),
  KEY `idx_attempted_at` (`attempted_at`),
  KEY `idx_success` (`success`),
  FOREIGN KEY (`batch_id`) REFERENCES `parse_batches`(`batch_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='检索尝试记录表';
```

### 7.5 文件夹监控配置表（folder_monitor_config）

配置文件夹监控的参数：

```sql
CREATE TABLE `folder_monitor_config` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `folder_path` VARCHAR(512) NOT NULL COMMENT '监控文件夹路径',
  `output_path` VARCHAR(512) NOT NULL COMMENT '结果输出路径',
  `scan_interval` INT NOT NULL DEFAULT 300 COMMENT '扫描间隔(秒)',
  `enable_formula` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '默认启用公式识别',
  `enable_table` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '默认启用表格识别',
  `max_file_size` BIGINT NOT NULL DEFAULT 15728640 COMMENT '最大文件大小(字节,默认15MB)',
  `supported_extensions` VARCHAR(100) NOT NULL DEFAULT 'pdf,doc,docx' COMMENT '支持的文件扩展名',
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用监控',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '配置创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '配置更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_folder_path` (`folder_path`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文件夹监控配置表';
```

## 8. API接口设计

### 8.1 解析文件夹接口

**接口路径**: `POST /api/parse-folder`

**请求参数**:
```json
{
  "folder_path": "/path/to/documents",
  "output_path": "/path/to/results",
  "enable_formula": true,
  "enable_table": true,
  "force_reparse": false,
  "ignore_parsed": true
}
```

参数说明：
- `ignore_parsed`: 是否忽略已解析文件，默认为true，设置为false时会重新解析所有文件

**响应格式**:
```json
{
  "code": 0,
  "message": "解析任务已提交",
  "data": {
    "batch_count": 5,
    "batch_ids": ["batch_001", "batch_002"],
    "estimated_completion": "2024-01-01T12:01:00Z"
  }
}
```

### 8.2 查询解析状态接口

**接口路径**: `GET /api/parse-status/{batch_id}`

**响应格式**:
```json
{
  "code": 0,
  "data": {
    "batch_id": "batch_001",
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z",
    "retrieved_at": "2024-01-01T12:01:30Z",
    "markdown_path": "/path/to/result.md",
    "progress": 100
  }
}
```

### 8.3 批次列表接口

**接口路径**: `GET /api/batch-list`

**查询参数**:
- `status`: 过滤状态
- `page`: 页码
- `limit`: 每页数量

**响应格式**:
```json
{
  "code": 0,
  "data": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "batches": [
      {
        "batch_id": "batch_001",
        "document_name": "example.pdf",
        "status": "completed",
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
}
```

## 9. 部署与配置

### 9.1 环境要求

- **Python**: 3.11.x
- **MySQL**: 8.0.34
- **MinIO**: 2024-05-07及以上稳定版
- **Redis**: 7.2.x（可选，用于缓存）

### 9.2 依赖包

```
fastapi==0.103.x
uvicorn==0.24.x
mysql-connector-python==8.2.x
requests==2.31.x
apscheduler==3.10.x
pydantic==2.5.x
python-multipart==0.0.6
```

### 9.3 配置文件

```yaml
# config.yaml
database:
  host: localhost
  port: 3306
  user: root
  password: password
  database: mineru_parse

mineru:
  api_key: your_api_key
  base_url: https://api.mineru.ai
  timeout: 300

storage:
  type: minio
  endpoint: localhost:9000
  access_key: minioadmin
  secret_key: minioadmin
  bucket: documents

scheduler:
  max_workers: 10
  job_defaults:
    coalesce: false
    max_instances: 3
```

## 10. 监控与日志

### 10.1 日志记录

- **解析任务日志**: 记录每个批次的处理过程
- **API访问日志**: 记录接口调用情况
- **错误日志**: 记录系统异常和错误信息
- **性能日志**: 记录处理时间和资源使用情况

### 10.2 监控指标

- **任务成功率**: 解析任务的成功完成比例
- **平均处理时间**: 从提交到完成的平均耗时
- **重试次数统计**: 各种错误的重试情况
- **系统资源使用**: CPU、内存、磁盘使用情况

## 11. 总结

本MinerU文档解析实现方案提供了完整的自动化文档处理流程，主要特点包括：

1. **自动增量解析**: 接口触发后自动扫描文件夹，通过`is_parsed`字段识别未解析的文件进行处理
2. **避免重复解析**: 在文档表中记录解析状态，已解析文件不再重复处理，提高系统效率
3. **智能调度机制**: 1分钟后自动获取结果，支持指数退避重试策略
4. **完整状态跟踪**: 详细记录解析状态、解析时间、batch_id等信息
5. **可靠性保障**: 定时检索未成功的任务，确保不遗漏任何文档
6. **灵活配置**: 支持多文件夹监控，可配置解析参数和重试策略

通过合理的数据库设计和模块化架构，系统能够高效处理大量文档，避免重复解析，为企业知识库建设提供可靠的文档解析服务。
