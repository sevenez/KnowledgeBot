# 向量搜索工具

## 简介

向量搜索工具是一个基于语义相似度的文档检索系统，它使用预训练的语言模型将查询文本转换为向量，然后在已构建的文档向量索引中查找最相似的内容。本工具与Milvus Lite向量数据库集成，支持双重向量存储方案。

## 功能特点

- 基于 BAAI/bge-m3 模型进行文本向量化
- 支持多索引搜索
- 自动查找和加载索引文件
- 支持 GPU 加速（如果可用）
- 交互式命令行界面
- 与Milvus Lite向量数据库集成，支持双重向量存储方案
- 兼容Document_Vectorization模块生成的向量数据

## 使用方法

### 环境准备

确保已安装以下依赖：
- torch
- transformers
- numpy
- pymilvus[lite]

可以使用以下命令检查环境：

```bash
python ../Document_Vectorization/check_environment.py
```

### 运行搜索工具

```bash
python vector_search.py
```

运行后，程序会自动查找并加载索引文件，然后进入交互式搜索界面。

### 搜索示例

```
=== 向量搜索工具 ===
搜索工具已准备就绪
输入'退出'结束搜索

请输入搜索查询: 公司的销售策略是什么

找到 5 个结果 (耗时: 0.123秒)

[1] 相似度: 0.8765
内容: 我们的销售策略主要包括四个方面：一是深耕重点行业，二是拓展新兴市场，三是提升客户体验，四是加强团队建设...
来源: 销售策略文档.md
文件: E:/AIstydycode/AIE/Project_EKBQA/DOCS/销售部/markdown/销售策略文档.md

[2] 相似度: 0.7654
内容: 销售团队需要定期分析市场趋势，调整销售策略，确保产品能够满足客户需求...
来源: 团队管理手册.txt
文件: E:/AIstydycode/AIE/Project_EKBQA/DOCS/销售部/txt/团队管理手册.txt
```

## 高级用法

### 在其他程序中使用

```python
from vector_search import VectorSearchTool

# 创建搜索工具实例
search_tool = VectorSearchTool()

# 执行搜索
results = search_tool.search("公司的销售策略是什么", top_k=5)

# 处理结果
for result in results:
    print(f"相似度: {result['similarity']}")
    print(f"内容: {result['metadata']['text'][:100]}...")
```

### 指定索引目录

```python
search_tool = VectorSearchTool(index_dir="path/to/indices")
```

### 禁用 GPU

```python
search_tool = VectorSearchTool(use_gpu=False)
```

## 故障排除

1. **找不到索引文件**
   - 确保已经运行过 Document_Vectorization/main.py 构建索引
   - 检查索引文件是否存在于以下目录之一：
     - source/Document_Vectorization/index_files
     - source/index_files
     - source/chunks_output/indices

2. **无法加载模型**
   - 确保模型已下载到本地
   - 检查网络连接
   - 尝试使用 check_environment.py 检查环境

3. **搜索结果不理想**
   - 尝试使用更具体的查询
   - 考虑重新构建索引，使用更小的文档切片大小
   - 尝试使用不同的索引类型（如 FLAT、HNSW 等）