-- 文档解析系统数据库表结构

-- 文档表（documents）
CREATE TABLE IF NOT EXISTS `doc_documents` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `path` VARCHAR(512) NOT NULL COMMENT '文件完整路径',
  `name` VARCHAR(256) NOT NULL COMMENT '文件名',
  `extension` VARCHAR(8) NOT NULL COMMENT '文件扩展名',
  `file_hash` VARCHAR(64) DEFAULT NULL COMMENT '文件内容哈希值',
  `size` BIGINT NOT NULL COMMENT '文件大小(字节)',
  `modified_time` DATETIME NOT NULL COMMENT '文件修改时间',
  `is_parsed` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已解析',
  `parsed_at` DATETIME NULL COMMENT '最近一次解析时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  `status` VARCHAR(1) NOT NULL DEFAULT '0' COMMENT '状态：0-未解析，1-已解析，2-已向量化',
  `knlg_base_code` VARCHAR(64) NULL COMMENT '知识库编号',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_path` (`path`),
  KEY `idx_name` (`name`),
  KEY `idx_modified_time` (`modified_time`),
  KEY `idx_is_parsed` (`is_parsed`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文档基本信息表';

-- 解析批次表（parse_batches）
CREATE TABLE IF NOT EXISTS `doc_parse_batches` (
  `batch_id` VARCHAR(64) NOT NULL COMMENT 'MinerU返回的批次ID',

  `document_id` BIGINT NOT NULL COMMENT '关联文档ID',
  `provider` VARCHAR(64) NOT NULL DEFAULT 'mineru' COMMENT '解析服务提供商',
  `enable_formula` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用公式识别',
  `enable_table` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用表格识别',
  `file_url` VARCHAR(512) DEFAULT NULL COMMENT '上传后的文件访问URL',
  `source_file_path` VARCHAR(512) NULL COMMENT '预处理前的源文件路径',
  `source_file_hash` VARCHAR(64) NULL COMMENT '预处理前的源文件哈希值',
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
  FOREIGN KEY (`document_id`) REFERENCES `doc_documents`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='解析批次信息表';

CREATE TABLE IF NOT EXISTS `doc_batch_retrieval_jobs` (
  `job_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `batch_id` VARCHAR(64) NOT NULL COMMENT '关联批次ID',
  `mineru_task_id` VARCHAR(64) NOT NULL COMMENT '提取任务 id，可用于查询任务结果',
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
  FOREIGN KEY (`batch_id`) REFERENCES `doc_parse_batches`(`batch_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='批次检索任务调度表';

-- 检索尝试记录表（retrieval_attempts）
CREATE TABLE IF NOT EXISTS `doc_retrieval_attempts` (
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
  FOREIGN KEY (`batch_id`) REFERENCES `doc_parse_batches`(`batch_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='检索尝试记录表';

-- 文件夹监控配置表（folder_monitor_config）
CREATE TABLE IF NOT EXISTS `doc_folder_monitor_config` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `folder_path` VARCHAR(512) NOT NULL COMMENT '监控文件夹路径',
  `output_path` VARCHAR(512) NOT NULL COMMENT '结果输出路径',
  `scan_interval` INT NOT NULL DEFAULT 300 COMMENT '扫描间隔(秒)',
  `enable_formula` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '默认启用公式识别',
  `enable_table` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '默认启用表格识别',
  `max_file_size` BIGINT NOT NULL DEFAULT 15728640 COMMENT '最大文件大小(字节,默认15MB)',
  `status` ENUM('active','inactive') NOT NULL DEFAULT 'active' COMMENT '配置状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_folder_path` (`folder_path`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文件夹监控配置表';

-- 文档分块表（document_chunks）
CREATE TABLE IF NOT EXISTS `doc_document_chunks` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `document_id` BIGINT NOT NULL COMMENT '关联文档ID',
  `file_id` BIGINT NOT NULL COMMENT '文件ID',
  `chunk_id` VARCHAR(64) NOT NULL COMMENT '分块唯一标识',
  `content` TEXT NOT NULL COMMENT '分块内容',
  `chunk_index` INT NOT NULL COMMENT '分块索引',
  `start_page` INT NULL COMMENT '起始页码',
  `end_page` INT NULL COMMENT '结束页码',
  `section_title` VARCHAR(256) NULL COMMENT '章节标题',
  `vector_id` VARCHAR(64) NULL COMMENT '向量存储ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_chunk_id` (`chunk_id`),
  KEY `idx_document_id` (`document_id`),
  KEY `idx_file_id` (`file_id`),
  KEY `idx_chunk_index` (`chunk_index`),
  KEY `idx_section_title` (`section_title`),
  FOREIGN KEY (`document_id`) REFERENCES `doc_documents`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文档分块存储表';

-- 文档元数据表（doc_metadata），上传文件由其他系统生成，本模块只调整status字段
CREATE TABLE `doc_metadata`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件路径',
  `file_url` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件url',
  `file_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件名',
  `file_extension` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件扩展名',
  `file_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文件类型',
  `file_size` bigint NOT NULL COMMENT '文件大小(字节)',
  `file_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '文件哈希值（后续优化）',
  `modified_time` datetime NOT NULL COMMENT '文件修改时间',
  `batch_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'MinerU解析batch_id，仅Word/PDF文件使用',
  `status` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '状态：0-未解析，1-md状态，2-向量化完成，3-图谱完成，4-已发布',
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` tinyint NOT NULL DEFAULT 0 COMMENT '删除标记（0:可用 1:已删除）',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_file_name`(`file_name` ASC) USING BTREE,
  INDEX `idx_batch_id`(`batch_id` ASC) USING BTREE,
  INDEX `idx_file_hash`(`file_hash` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 61 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '文件元数据表' ROW_FORMAT = Dynamic;