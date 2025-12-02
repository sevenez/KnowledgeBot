# 文档向量化与索引构建模块

*更新时间：2025年9月7日*

## 概述

本模块负责将企业文档转换为向量表示并构建搜索索引，使用Milvus Lite向量数据库存储，实现高效的向量检索。

## 核心功能

### 1. 文档处理
- **多格式支持**：支持 `.txt`、`.md`、`.csv`、`.xlsx` 等格式
- **智能切片**：根据文档类型选择最优切片策略
- **内容清理**：保留标点符号，只移除控制字符
- **增量处理**：跳过已处理文件，提高效率

### 2. 向量化
- **模型**：使用 BAAI/bge-m3 中文向量模型
- **离线支持**：支持本地模型缓存，无需重复下载
- **GPU加速**：自动检测并使用GPU（如可用）
- **批处理**：支持批量向量化，提高处理效率

### 3. 向量存储与索引构建
- **Milvus Lite向量数据库**：使用嵌入式向量数据库作为主要存储
- **多种索引类型**：支持 FLAT、IVF 等索引类型
- **元数据管理**：完整保存文档元信息
- **增量更新**：支持向量存储和索引的增量构建

## 文件结构

```
Document_Vectorization/
├── main.py                    # 主程序（处理所有文件，使用Milvus）
├── main_lite.py              # 轻量版（处理前6个文件，用于测试）
├── check_environment.py      # 环境检查工具
├── document_chunking.py      # 文档切片模块
├── text_vectorization.py    # 文本向量化模块
├── vector_storage.py         # 向量存储模块（Milvus实现）
└── README.md                 # 本文档
```

## 快速开始

### 1. 环境检查
```bash
# 检查环境是否满足要求
python source/Document_Vectorization/check_environment.py

# 显示安装提示（如有缺失库）
python source/Document_Vectorization/check_environment.py --install
```

### 2. 安装依赖
```bash
pip install torch transformers pandas pymilvus[lite]
```

### 3. 运行程序

#### 轻量版（推荐用于测试）
```bash
# 处理前6个文件（各目录3个）
python source/Document_Vectorization/main_lite.py

# 重新处理所有文件
python source/Document_Vectorization/main_lite.py --reprocess

# 仅检查环境
python source/Document_Vectorization/main_lite.py --check-only

# 自定义文件数量
python source/Document_Vectorization/main_lite.py --max-files 12
```

#### 完整版（处理所有文件）
```bash
# 增量处理（跳过已处理文件）
python source/Document_Vectorization/main.py

# 重新处理所有文件
python source/Document_Vectorization/main.py --reprocess

# 指定索引类型
python source/Document_Vectorization/main.py --index-type IVF

# 仅检查环境
python source/Document_Vectorization/main.py --check-only
```

## 处理的文档目录

1. **MD_result目录**：处理所有 `.md` 格式文件
2. **DOCS目录**：处理 `.txt`、`.csv`、`.xlsx`、`.md` 格式文件

## 输出结果

### 文件结构
```
source/chunks_output/
├── [文件名]_chunks.json      # 每个文档的切片和向量
└── indices/                  # 完整版索引目录
    ├── metadata.json        # 索引元数据
    └── id_metadata.json     # ID到文档的映射
```

### JSON格式示例
```json
[
  {
    "text": "文档内容片段",
    "vector": [0.1, 0.2, ...],
    "metadata": {
      "source": "文件名",
      "chunk_id": 0,
      "file_path": "完整路径",
      "chunk_type": "text"
    }
  }
]
```

## 配置参数

### 文档切片参数
- `chunk_size`: 切片大小（默认500字符）
- `chunk_overlap`: 切片重叠（默认50字符）
- `min_chunk_size`: 最小切片大小（默认50字符）

### 向量化参数
- `model_name`: 模型名称（默认 BAAI/bge-m3）
- `max_length`: 最大序列长度（默认512）
- `batch_size`: 批处理大小（默认32）

### 索引参数
- `index_type`: 索引类型（FLAT/IVF，默认FLAT）
- `use_gpu`: 是否使用GPU（自动检测）

## 环境要求

### 必需依赖
- Python 3.8+
- torch >= 1.9.0
- transformers >= 4.20.0
- pandas >= 1.3.0
- pymilvus[lite] >= 2.4.0

### 可选依赖
- CUDA（用于GPU加速）
- openpyxl（用于Excel文件处理）

### 系统要求
- 内存：建议8GB+
- 存储：模型缓存需要2-3GB空间
- 网络：首次运行需要下载模型

## 故障排除

### 常见问题

1. **模型下载失败**
   ```bash
   # 检查网络连接，或使用代理
   export HF_ENDPOINT=https://hf-mirror.com
   ```

2. **内存不足**
   ```bash
   # 减少批处理大小
   python main.py --batch-size 16
   ```

3. **GPU不可用**
   ```bash
   # 检查CUDA安装
   python -c "import torch; print(torch.cuda.is_available())"
   ```

4. **文件编码问题**
   - 确保文档使用UTF-8编码
   - 检查文件路径中是否包含特殊字符

### 日志信息
程序运行时会输出详细的日志信息，包括：
- 环境检查结果
- 文件处理进度
- 向量化耗时
- 索引构建状态

## 性能优化

### 建议配置
- **GPU环境**：使用CUDA加速，处理速度提升5-10倍
- **SSD存储**：提高文件读写速度
- **充足内存**：避免频繁的磁盘交换

### 批处理优化
- 小文档：增大batch_size（如64）
- 大文档：减小batch_size（如16）
- GPU内存限制：动态调整batch_size

## 扩展功能

### 自定义模型
可以替换为其他向量模型：
```python
# 在text_vectorization.py中修改
model_name = "your-custom-model"
```

### 自定义切片策略
可以在document_chunking.py中添加新的切片方法：
```python
def custom_chunk_method(self, content, file_path, file_id):
    # 自定义切片逻辑
    pass
```

## 版本历史

- **v1.3** (2025-08-27)
  - 修复标点符号删除问题
  - 添加轻量版测试工具
  - 改进错误处理和日志输出
  - 优化索引构建性能

- **v1.2** (2025-08-27)
  - 添加增量处理功能
  - 支持多种索引类型
  - 改进环境检查工具

- **v1.1** (2025-08-27)
  - 添加离线模式支持
  - 优化内存使用
  - 修复兼容性问题

- **v1.0** (2025-08-27)
  - 初始版本发布
  - 基础文档处理和向量化功能

## 技术支持

如遇到问题，请检查：
1. 环境检查结果
2. 日志错误信息
3. 系统资源使用情况
4. 网络连接状态

更多技术细节请参考各模块的源代码注释。