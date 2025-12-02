# FastAPI 文件处理器

基于FastAPI的文档预处理接口服务，提供RESTful API来处理单个文件并获取解析结果。

## 📁 项目结构

```
source/FastAPI_Processor/
├── __init__.py          # 模块初始化文件
├── main.py              # 主程序，FastAPI应用
├── requirements.txt     # 依赖包列表
├── run_server.py       # 服务启动脚本
├── api_client.py       # Python客户端示例
└── README.md           # 说明文档
```

## 🚀 功能特性

- ✅ **单个文件处理** - 接收文件路径进行处理
- ✅ **自动解析** - 调用MinerU进行文档解析
- ✅ **定时等待** - 等待指定时间后获取结果
- ✅ **状态查询** - 实时查询处理状态
- ✅ **异步处理** - 后台异步处理，不阻塞请求
- ✅ **完整API** - 提供RESTful接口和文档

## 📋 API端点

### 基础信息
- `GET /` - 获取API基本信息
- `GET /docs` - 交互式API文档
- `GET /redoc` - ReDoc API文档

### 文件处理
- `POST /batch-process` - 批量处理文档任务（支持单个文件）
- `GET /status/{task_id}` - 获取任务状态
- `GET /batch-status/{batch_id}` - 获取批量任务状态

## 🛠️ 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install fastapi uvicorn requests pydantic
```

## 🎯 快速开始

### 方法1: 使用启动脚本（推荐）
```bash
# 默认配置启动
python run_server.py

# 自定义端口启动
python run_server.py --port 8080

# 开发模式（热重载）
python run_server.py --reload

# 多进程模式
python run_server.py --workers 4
```

### 方法2: 直接运行主程序
```bash
python main.py
```

### 方法3: 使用uvicorn直接运行
```bash
uvicorn FastAPI_Processor.main:app --host 0.0.0.0 --port 8271
```

## 📝 使用示例

### Python客户端调用

```python
from FastAPI_Processor.api_client import FastAPIClient

# 创建客户端
client = FastAPIClient("http://localhost:8271")

# 处理文件
result = client.process_file("文件路径", wait_time=30)

if result["success"]:
    task_id = result["task_id"]
    print(f"任务已启动: {task_id}")
    
    # 等待完成
    status = client.wait_for_completion(task_id)
    print(f"处理结果: {status}")
```

### curl命令行调用

```bash
# 启动处理
curl -X POST "http://localhost:8271/process" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "文件路径", "wait_time": 30}'

# 检查状态
curl "http://localhost:8271/status/任务ID"

# 查看所有任务
curl "http://localhost:8271/tasks"
```

### 请求示例

**启动处理:**
```json
{
  "file_path": "e:/AIstydycode/AIE/Gitee_EKBQA/DOCS/产研部/txt/文档.txt",
  "wait_time": 30
}
```

**响应:**
```json
{
  "success": true,
  "message": "文件处理已启动，任务ID: 1735622400",
  "task_id": "1735622400"
}
```

## 🔧 配置说明

### 环境要求
- Python 3.7+
- MySQL数据库（用于存储处理记录）
- MinerU API访问权限

### 数据库配置
确保 `../db_config.py` 配置正确：

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': '企业知识库问答系统',
    'charset': 'utf8mb4'
}
```

### API配置
确保 `../api_config.py` 配置正确：

```python
MINERU_API = {
    'key': '你的API密钥',
    'url': 'https://mineru.net/api/v4/file-urls/batch',
    'max_files_per_batch': 200
}
```

## 📊 处理流程

1. **接收请求** - 客户端发送文件路径
2. **验证文件** - 检查文件是否存在
3. **提交解析** - 调用MinerU API提交文件
4. **等待处理** - 等待指定时间（默认30秒）
5. **获取结果** - 从MinerU获取解析结果
6. **返回状态** - 返回处理结果和文件路径

## 🐛 故障排除

### 常见问题

1. **连接拒绝**
   - 检查服务是否启动：`netstat -an | find "8271"`
   - 检查防火墙设置

2. **文件不存在**
   - 检查文件路径是否正确
   - 确保文件有读取权限

3. **数据库连接失败**
   - 检查MySQL服务状态
   - 验证数据库配置

4. **API密钥无效**
   - 更新 `api_config.py` 中的密钥

### 日志查看

服务运行时会输出详细日志：
```
2025-08-31 12:00:00 - FastAPIFileProcessor - INFO - 开始处理任务 1735622400, 文件: 文件路径
2025-08-31 12:00:05 - FastAPIFileProcessor - INFO - 文件提交成功，MinerU任务ID: mineru-12345
```

## 🔄 开发说明

### 代码结构
- **main.py** - 主应用，包含所有API端点
- **api_client.py** - 客户端库，方便调用API
- **run_server.py** - 启动脚本，支持多种配置

### 扩展功能
如需添加新功能：
1. 在 `main.py` 中添加新的API端点
2. 更新 `api_client.py` 中的客户端方法
3. 添加相应的数据模型

## 📞 技术支持

如有问题，请检查：
1. 服务日志输出
2. 数据库连接状态
3. MinerU API可用性
4. 文件系统权限

## 📄 许可证

本项目基于现有文档预处理系统构建，遵循原有项目的许可证协议。

---

**注意**: 使用前请确保配置正确的数据库连接和MinerU API密钥。